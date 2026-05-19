import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select, and_
from app.db import AsyncSessionLocal
from app.models.user import User
from app.models.sessions import Session
from app.models.pendingMedia import PendingMedia
from app.services.onboarding_service import onboarding_service
from app.services.agent_dispatcher import agent_dispatcher
from app.services.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)

class WebhookRouter:
    """
    Service chargé de router les messages entrants vers le service approprié :
    soit l'onboarding (si pas de session active), soit l'agent IA.
    """
    
    async def route_message(self, phone: str, text: Optional[str] = None, interactive_id: Optional[str] = None):
        """
        Analyse l'état de l'utilisateur et route le message.
        """
        # 1. Vérifier d'abord si c'est un utilisateur Yaburu
        from app.services.yaburu_service import yaburu_service
        yaburu_data = await yaburu_service.check_user(phone)
        
        if not yaburu_data:
            logger.warning(f"🚫 Accès refusé pour {phone}. Non trouvé sur Yaburu.")
            await whatsapp_service.send_text_message(phone, "Désolé, votre numéro n'est pas associé à un compte Yaburu actif. Veuillez contacter le support si c'est une erreur.")
            return "ACCESS_DENIED"

        async with AsyncSessionLocal() as db:
            # 2. Synchroniser ou créer l'utilisateur et ses boutiques
            user = await onboarding_service.handle_user_connection(db, phone, yaburu_data)
            
            # 3. Vérifier s'il y a une session active (avec auto-nettoyage)
            active_session = None
            session_result = await db.execute(
                select(Session).where(
                    and_(
                        Session.user_id == user.id,
                        Session.is_active == True,
                        Session.expires_at > datetime.utcnow()
                    )
                ).order_by(Session.created_at.desc())
            )
            active_sessions = session_result.scalars().all()
            
            if active_sessions:
                active_session = active_sessions[0]
                
                # Self-healing : désactiver les autres sessions actives en doublon
                if len(active_sessions) > 1:
                    logger.warning(f"🧹 Self-Healing : Désactivation de {len(active_sessions) - 1} sessions actives en doublon pour l'utilisateur {user.id}")
                    for s in active_sessions[1:]:
                        s.is_active = False
                    await db.commit()
            
            # 4. Gérer la conversation
            if active_session:
                from app.models.conversations import Conversation
                conv_result = await db.execute(
                    select(Conversation).where(
                        and_(
                            Conversation.user_id == user.id,
                            Conversation.store_id == active_session.store_id,
                            Conversation.status == "active"
                        )
                    ).order_by(Conversation.last_message_at.desc())
                )
                conversations = conv_result.scalars().all()
                conversation = conversations[0] if conversations else None
                
                # Self-healing : archiver les autres conversations actives en doublon
                if conversations and len(conversations) > 1:
                    logger.warning(f"🧹 Self-Healing : Archivage de {len(conversations) - 1} conversations actives en doublon pour l'utilisateur {user.id}")
                    for c in conversations[1:]:
                        c.status = "archived"
                    await db.commit()
                
                if not conversation:
                    conversation = Conversation(
                        user_id=user.id,
                        store_id=active_session.store_id,
                        session_id=active_session.id,
                        title=f"Conversation WhatsApp {datetime.now().strftime('%Y-%m-%d')}"
                    )
                    db.add(conversation)
                    await db.commit()
                    await db.refresh(conversation)
                
                conversation_id = str(conversation.id)
                logger.info(f"✅ Session active trouvée pour {phone}. Routage vers l'AGENT.")
                
                conversation.last_message_at = datetime.now()
                await db.commit()

                if text:
                    await agent_dispatcher.handle_agent_message(active_session, phone, text, conversation_id)
                elif interactive_id:
                    await agent_dispatcher.handle_agent_message(active_session, phone, f"[Interaction: {interactive_id}]", conversation_id)
                return "ROUTED_TO_AGENT"
            else:
                logger.info(f"ℹ️ Pas de session active pour {phone}. Routage vers l'ONBOARDING.")
                return await onboarding_service.process_onboarding_step(db, user, phone, text, interactive_id)

    async def handle_media_message(self, phone: str, media_id: str, media_type: str):
        """
        Gère la réception d'un média : téléchargement et mise en attente.
        """
        logger.info(f"📸 Réception d'un média ({media_type}) de {phone}. ID: {media_id}")
        
        # 1. Simuler le téléchargement
        file_path = await whatsapp_service.download_media(media_id)
        
        # 2. Enregistrer en base de données
        async with AsyncSessionLocal() as db:
            pending = PendingMedia(
                phone=phone,
                media_id=media_id,
                file_path=file_path,
                media_type=media_type
            )
            db.add(pending)
            await db.commit()
            logger.info(f"💾 Média {media_id} mis en attente pour {phone}")

webhook_router = WebhookRouter()
