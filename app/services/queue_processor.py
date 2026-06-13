import asyncio
import logging
from datetime import datetime
from sqlalchemy import select, delete, and_
from sqlalchemy.orm import selectinload
from app.db import AsyncSessionLocal
from app.models.user import User
from app.models.messageQueue import MessageQueue
from app.models.sessions import Session
from app.services.onboarding_service import onboarding_service
from app.services.agent_dispatcher import agent_dispatcher
from app.services.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)

# Ensemble en mémoire pour éviter le lancement en double d'un worker asynchrone sur la même instance
active_processors = set()

# Dictionnaire pour le debounce en mémoire
# Clé : phone, Valeur : timestamp du dernier message reçu
last_activity: dict[str, float] = {}

# File d'attente des messages en mémoire (remplace la table MessageQueue)
# Clé : phone, Valeur : liste de textes
pending_messages: dict[str, list] = {}

# Compteur de requêtes webhook actuellement en cours de préparation (avant insertion en file)
in_flight_requests: dict[str, int] = {}

async def process_user_queue(phone: str):
    """
    Worker asynchrone qui traite la file d'attente des messages d'un utilisateur.
    Réalise l'anti-rebond (debounce glissant) et la coalescence (fusion des messages).
    """
    logger.info(f" [QUEUE] Démarrage du processeur de file pour {phone}...")
    # Note: phone est déjà ajouté à active_processors par webhook_router avant create_task
    # On s'assure quand même qu'il y est (cas de relance directe)
    active_processors.add(phone)
    
    try:
        import time
        from sqlalchemy import func
        # ── Debounce glissant 100% en RAM ─────────────────────────────────────────────────
        DEBOUNCE_WINDOW = 1.5   # secondes sans nouveau message avant de traiter
        POLL_INTERVAL   = 0.1   # fréquence de vérification de la RAM
        
        while True:
            # 1. Boucle de Debounce
            while True:
                # On bloque le chrono tant qu'un autre webhook est EN COURS de préparation (DB, téléchargements)
                if in_flight_requests.get(phone, 0) == 0:
                    last_time = last_activity.get(phone, time.time())
                    if (time.time() - last_time) >= DEBOUNCE_WINDOW:
                        break
                await asyncio.sleep(POLL_INTERVAL)

            logger.info(f"✅ [QUEUE] Fenêtre de silence atteinte pour {phone}. Traitement des messages en file.")
            # ─────────────────────────────────────────────────────────────────────

            # 2. Récupérer les messages en mémoire
            queued_messages = pending_messages.pop(phone, [])
            
            if not queued_messages:
                # Retrait SYNCHRONE du verrou mémoire pour éviter toute Race Condition avant l'arrêt complet
                active_processors.discard(phone)
                break

            # 3. Coalescence (Fusion des textes)
            combined_text = "\n".join(queued_messages)

            # 5. Exécuter la logique de routage métier sur le message fusionné
            logger.info(f"🔄 [QUEUE] Consommation de {len(queued_messages)} message(s) pour {phone}.")
            await execute_routing_logic(phone, combined_text)
            
            # Vérifier si de nouveaux messages sont arrivés pendant l'exécution
            if not pending_messages.get(phone):
                # Retrait SYNCHRONE du verrou
                active_processors.discard(phone)
                break

    except Exception as e:
        logger.error(f"❌ [QUEUE] Erreur critique dans le processeur de file pour {phone} : {e}")
        # Notifier l'utilisateur via WhatsApp
        try:
            err_str = str(e)
            if "429" in err_str or "rate limit" in err_str.lower() or "provider returned error" in err_str.lower():
                user_msg = "⏳ Le service est momentanément surchargé. Veuillez renvoyer votre message dans quelques secondes."
            else:
                user_msg = "⚠️ Une erreur technique est survenue. Veuillez réessayer dans un instant."
            await whatsapp_service.send_text_message(phone, user_msg)
        except Exception as notify_err:
            logger.error(f"❌ [QUEUE] Impossible d'envoyer le message d'erreur à {phone} : {notify_err}")
    finally:
        # S'assurer de nettoyer la base de données uniquement à la toute fin
        try:
            async with AsyncSessionLocal() as db:
                user_res = await db.execute(select(User).where(User.telephone == phone))
                user = user_res.scalar_one_or_none()
                if user:
                    user.traitement_en_cours = False
                    await db.commit()
                    logger.info(f"🔓 [QUEUE] Traitement terminé. Verrou DB libéré pour {phone}.")
        except Exception as lock_err:
            logger.error(f"❌ [QUEUE] Échec de la libération du verrou DB final : {lock_err}")
            
        # S'assurer que le cache Yaburu est nettoyé
        from app.services.webhook_router import yaburu_data_cache
        yaburu_data_cache.pop(phone, None)

async def execute_routing_logic(phone: str, text: str):
    """
    Logique de routage similaire à celle du webhook, mais opérant sur le message consolidé.
    """
    from app.models.conversations import Conversation
    
    async with AsyncSessionLocal() as db:
        # 1. Requête optimisée : Jointure Session, User et Conversation
        # Cela réduit drastiquement les allers-retours vers la base de données.
        from sqlalchemy.orm import joinedload, contains_eager
        
        res = await db.execute(
            select(Session, User, Conversation)
            .join(User, Session.utilisateur_id == User.id)
            .outerjoin(Conversation, and_(
                Conversation.session_id == Session.id,
                Conversation.status == "active"
            ))
            .where(
                and_(
                    User.telephone == phone,
                    Session.est_active == True,
                    Session.expire_le > datetime.utcnow()
                )
            ).order_by(Session.date_creation.desc(), Conversation.dernier_message_le.desc())
        )
        
        # Grouper les résultats
        rows = res.all()
        
        if rows:
            # On prend la première session active trouvée
            active_session = rows[0][0]
            user = rows[0][1]
            
            # Récupérer toutes les conversations actives liées à cette session parmi les résultats
            conversations = []
            for r in rows:
                if r[2] and r[2] not in conversations:
                    conversations.append(r[2])
                    
            conversation = conversations[0] if conversations else None
            
            if len(conversations) > 1:
                logger.warning(f"🧹 Self-Healing : Archivage de {len(conversations) - 1} conversations actives en doublon.")
                for c in conversations[1:]:
                    c.status = "archived"
                await db.commit()
            
            if not conversation:
                logger.info(f"🆕 Création d'une nouvelle conversation active pour la session {active_session.id}")
                
                # Récupérer la dernière conversation de l'utilisateur pour la résumer
                last_conv_res = await db.execute(
                    select(Conversation).join(Session, Session.id == Conversation.session_id)
                    .where(Session.utilisateur_id == user.id)
                    .order_by(Conversation.date_creation.desc()).limit(1)
                )
                last_conv = last_conv_res.scalar_one_or_none()
                
                summary = None
                if last_conv:
                    # Tâche asynchrone pour ne pas bloquer la réponse immédiate du bot
                    from app.agent.service import agent_service
                    async def update_summary_bg(conv_to_update_id, old_conv_id):
                        try:
                            await asyncio.sleep(1) # Attendre un peu que le process principal libère la DB
                            sum_text = await agent_service.generate_summary(str(old_conv_id))
                            async with AsyncSessionLocal() as bg_db:
                                from app.models.conversations import Conversation as BgConv
                                conv = await bg_db.execute(select(BgConv).where(BgConv.id == conv_to_update_id))
                                conv_obj = conv.scalar_one_or_none()
                                if conv_obj:
                                    conv_obj.resume_precedent = sum_text
                                    await bg_db.commit()
                                    logger.info(f"📝 Résumé généré et sauvegardé en arrière-plan.")
                        except Exception as e:
                            logger.error(f"❌ Erreur lors de la génération asynchrone du résumé: {e}")
                
                conversation = Conversation(
                    session_id=active_session.id,
                    title=f"Conversation WhatsApp {datetime.now().strftime('%Y-%m-%d')}",
                    resume_precedent=None # Sera rempli par la tâche asynchrone
                )
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
                is_first_message = True
                
                # Lancement du résumé d'historique en tâche de fond
                if last_conv:
                    asyncio.create_task(update_summary_bg(conversation.id, last_conv.id))
            else:
                is_first_message = False
            
            conversation_id = str(conversation.id)
            conversation.dernier_message_le = datetime.now()
            await db.commit()

            if text:
                logger.info(f"🤖 [QUEUE] Routage du message consolidé directement vers l'AGENT (Session active bypass).")
                await agent_dispatcher.handle_agent_message(
                    active_session, phone, text, conversation_id, str(user.id),
                    is_first_message=is_first_message
                )
            return


    # 2. Si aucune session active locale n'est trouvée, passer par le processus complet d'authentification externe Yaburu
    logger.info(f"ℹ️ Pas de session active locale pour {phone}. Authentification requise auprès de Yaburu API...")
    
    from app.services.webhook_router import yaburu_data_cache
    from app.services.yaburu_service import yaburu_service
    yaburu_data = yaburu_data_cache.get(phone)
    if not yaburu_data:
        logger.warning(f"⚠️ [QUEUE] Cache Yaburu manquant pour {phone}, appel HTTP de secours...")
        yaburu_data = await yaburu_service.check_user(phone)

    if not yaburu_data:
        logger.warning(f"🚫 Accès refusé pour {phone}. Non trouvé sur Yaburu.")
        await whatsapp_service.send_text_message(
            phone,
            "Désolé, votre numéro n'est pas associé à un compte Yaburu actif. Veuillez contacter le support si c'est une erreur."
        )
        return

    async with AsyncSessionLocal() as db:
        # Synchroniser ou créer l'utilisateur et ses boutiques
        user = await onboarding_service.handle_user_connection(db, phone, yaburu_data)
        
        # Routage vers l'onboarding car il n'y a pas de session active
        logger.info(f"ℹ️ Routage vers l'ONBOARDING pour {phone}.")
        await onboarding_service.process_onboarding_step(db, user, phone, text)
