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
        # ── Debounce glissant ─────────────────────────────────────────────────
        # On attend jusqu'à ce qu'aucun nouveau message n'arrive pendant DEBOUNCE_WINDOW secondes.
        # Toutes les POLL_INTERVAL secondes on vérifie si la file a grossi.
        DEBOUNCE_WINDOW = 0.5   # secondes sans nouveau message avant de traiter (réduit pour + de vitesse)
        POLL_INTERVAL   = 0.2   # fréquence de sondage de la file (réduit pour + de réactivité)
        
        last_count = 0
        silence_elapsed = 0.0

        while silence_elapsed < DEBOUNCE_WINDOW:
            await asyncio.sleep(POLL_INTERVAL)
            silence_elapsed += POLL_INTERVAL

            # Compter les messages actuellement en file
            async with AsyncSessionLocal() as db:
                res = await db.execute(
                    select(MessageQueue)
                    .where(MessageQueue.phone == phone)
                )
                current_count = len(res.scalars().all())

            if current_count > last_count:
                # Nouveau(x) message(s) détecté(s) → on réinitialise le compteur de silence
                logger.info(
                    f"🔄 [QUEUE] {current_count - last_count} nouveau(x) message(s) reçu(s) pour {phone}. "
                    f"Réinitialisation du debounce."
                )
                last_count = current_count
                silence_elapsed = 0.0  # reset

        logger.info(f"✅ [QUEUE] Fenêtre de silence atteinte pour {phone}. Traitement de {last_count} message(s).")
        # ─────────────────────────────────────────────────────────────────────

        try:
            while True:
                async with AsyncSessionLocal() as db:
                    # Récupérer tous les messages en attente pour ce numéro
                    res = await db.execute(
                        select(MessageQueue)
                        .where(MessageQueue.phone == phone)
                        .order_by(MessageQueue.created_at.asc())
                    )
                    queued_messages = res.scalars().all()

                    if not queued_messages:
                        # Plus de message dans la file, on libère le verrou
                        user_res = await db.execute(
                            select(User).where(User.telephone == phone)
                        )
                        user = user_res.scalar_one_or_none()
                        if user:
                            user.traitement_en_cours = False
                            await db.commit()
                            logger.info(f"🔓 [QUEUE] File d'attente vide. Verrou de traitement libéré pour {phone}.")
                        break

                    # 3. Coalescence (Fusion des textes)
                    texts_to_combine = []
                    for msg in queued_messages:
                        if msg.text:
                            texts_to_combine.append(msg.text)
                    
                    combined_text = "\n".join(texts_to_combine)

                    # 4. Supprimer les messages traités de la file
                    msg_ids = [m.id for m in queued_messages]
                    await db.execute(
                        delete(MessageQueue).where(MessageQueue.id.in_(msg_ids))
                    )
                    await db.commit()

                # 5. Exécuter la logique de routage métier sur le message fusionné
                logger.info(f"🔄 [QUEUE] Consommation de {len(queued_messages)} message(s) pour {phone}.")
                await execute_routing_logic(phone, combined_text)

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
            # Libérer le verrou DB
            try:
                async with AsyncSessionLocal() as db:
                    user_res = await db.execute(
                        select(User).where(User.telephone == phone)
                    )
                    user = user_res.scalar_one_or_none()
                    if user:
                        user.traitement_en_cours = False
                        await db.commit()
                        logger.info(f"🔓 [QUEUE] Verrou libéré suite à une exception pour {phone}.")
            except Exception as lock_err:
                logger.error(f"❌ [QUEUE] Échec de la libération du verrou post-erreur : {lock_err}")
    finally:
        # S'assurer de libérer le verrou en mémoire à la toute fin
        active_processors.discard(phone)
        # Nettoyer le cache Yaburu pour ce numéro (libération mémoire)
        from app.services.webhook_router import yaburu_data_cache
        yaburu_data_cache.pop(phone, None)

async def execute_routing_logic(phone: str, text: str):
    """
    Logique de routage similaire à celle du webhook, mais opérant sur le message consolidé.
    """
    async with AsyncSessionLocal() as db:
        # 1. Vérifier en premier s'il y a une session active en base locale
        from app.models.stores import store as StoreModel
        session_result = await db.execute(
            select(Session)
            .options(selectinload(Session.store))
            .join(StoreModel, Session.boutique_id == StoreModel.id)
            .join(User, StoreModel.utilisateur_id == User.id)
            .where(
                and_(
                    User.telephone == phone,
                    Session.est_active == True,
                    Session.expire_le > datetime.utcnow()
                )
            ).order_by(Session.date_creation.desc())
        )
        active_sessions = session_result.scalars().all()
        
        if active_sessions:
            active_session = active_sessions[0]
            if len(active_sessions) > 1:
                logger.warning(f"🧹 Self-Healing : Désactivation de {len(active_sessions) - 1} sessions en doublon.")
                for s in active_sessions[1:]:
                    s.est_active = False
                await db.commit()
                
            # Récupérer l'utilisateur correspondant
            user_res = await db.execute(
                select(User).where(User.telephone == phone)
            )
            user = user_res.scalar_one_or_none()
            
            # Gérer la conversation active et router vers l'Agent
            from app.models.conversations import Conversation
            conv_result = await db.execute(
                select(Conversation).where(
                    and_(
                        Conversation.session_id == active_session.id,
                        Conversation.status == "active"
                    )
                ).order_by(Conversation.dernier_message_le.desc())
            )
            conversations = conv_result.scalars().all()
            conversation = conversations[0] if conversations else None
            
            if conversations and len(conversations) > 1:
                logger.warning(f"🧹 Self-Healing : Archivage de {len(conversations) - 1} conversations actives en doublon.")
                for c in conversations[1:]:
                    c.status = "archived"
                await db.commit()
            
            if not conversation:
                logger.info(f"🆕 Création d'une nouvelle conversation active pour la session {active_session.id}")
                conversation = Conversation(
                    session_id=active_session.id,
                    title=f"Conversation WhatsApp {datetime.now().strftime('%Y-%m-%d')}"
                )
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
                is_first_message = True
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
