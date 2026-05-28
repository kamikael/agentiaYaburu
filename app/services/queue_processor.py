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
    logger.info(f"⏳ [QUEUE] Démarrage du processeur de file pour {phone}...")
    # Note: phone est déjà ajouté à active_processors par webhook_router avant create_task
    # On s'assure quand même qu'il y est (cas de relance directe)
    active_processors.add(phone)
    
    try:
        # ── Debounce glissant ─────────────────────────────────────────────────
        # On attend jusqu'à ce qu'aucun nouveau message n'arrive pendant DEBOUNCE_WINDOW secondes.
        # Toutes les POLL_INTERVAL secondes on vérifie si la file a grossi.
        DEBOUNCE_WINDOW = 3.0   # secondes sans nouveau message avant de traiter
        POLL_INTERVAL   = 0.5   # fréquence de sondage de la file
        
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
            # En cas d'erreur fatale, s'assurer de libérer le verrou
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

async def execute_routing_logic(phone: str, text: str):
    """
    Logique de routage similaire à celle du webhook, mais opérant sur le message consolidé.
    """
    # 1. Vérifier si c'est un utilisateur Yaburu
    from app.services.yaburu_service import yaburu_service
    yaburu_data = await yaburu_service.check_user(phone)
    
    if not yaburu_data:
        logger.warning(f"🚫 Accès refusé pour {phone}. Non trouvé sur Yaburu.")
        await whatsapp_service.send_text_message(
            phone,
            "Désolé, votre numéro n'est pas associé à un compte Yaburu actif. Veuillez contacter le support si c'est une erreur."
        )
        return

    async with AsyncSessionLocal() as db:
        # 2. Synchroniser ou créer l'utilisateur et ses boutiques
        user = await onboarding_service.handle_user_connection(db, phone, yaburu_data)
        
        # 3. Vérifier s'il y a une session active
        from app.models.stores import store as StoreModel
        active_session = None
        session_result = await db.execute(
            select(Session)
            .options(selectinload(Session.store))
            .join(StoreModel, Session.boutique_id == StoreModel.id)
            .where(
                and_(
                    StoreModel.utilisateur_id == user.id,
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
                    s.is_active = False
                await db.commit()
        
        # 4. Gérer la conversation active et router
        if active_session:
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
            
            conversation_id = str(conversation.id)
            conversation.dernier_message_le = datetime.now()
            await db.commit()

            if text:
                logger.info(f"🤖 [QUEUE] Routage du message consolidé vers l'AGENT.")
                await agent_dispatcher.handle_agent_message(
                    active_session, phone, text, conversation_id, str(user.id)
                )
        else:
            logger.info(f"ℹ️ Pas de session active pour {phone}. Routage vers l'ONBOARDING.")
            await onboarding_service.process_onboarding_step(db, user, phone, text)
