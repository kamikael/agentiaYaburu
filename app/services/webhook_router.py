import logging
import asyncio
from datetime import datetime
from typing import Optional, Any, Dict
from sqlalchemy import select, and_
from app.db import AsyncSessionLocal
from app.models.user import User
from app.models.sessions import Session
from app.models.pendingMedia import PendingMedia
from app.models.messageQueue import MessageQueue
from app.services.onboarding_service import onboarding_service
from app.services.agent_dispatcher import agent_dispatcher
from app.services.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)

# Cache en mémoire : évite de rappeler check_user dans queue_processor
# Clé : phone, Valeur : yaburu_data déjà récupéré par webhook_router
yaburu_data_cache: Dict[str, Any] = {}

class WebhookRouter:
    
    """
    Service chargé de router les messages entrants vers la file d'attente
    et de déclencher le traitement asynchrone (coalescence / queueing).
    """
    
    async def route_message(self, phone: str, text: Optional[str] = None, audio: Optional[Any] = None, image: Optional[Any] = None, quoted_text: Optional[str] = None, quoted_image: Optional[Any] = None, quoted_audio: Optional[Any] = None):
        """
        Analyse l'état de l'utilisateur, pré-traite le média, formate les citations
        et ajoute le message résultant dans la file d'attente pour exécution asynchrone.
        """
        # Si c'est un message audio (note vocale), on le télécharge et on le transcrit en texte brut via OpenAI Whisper
        if audio:
            audio_url = getattr(audio, "url", None) or (audio.get("url") if isinstance(audio, dict) else None)
            if audio_url:
                try:
                    # 1. Téléchargement réel du média audio
                    media_key = getattr(audio, "mediaKey", None) or (audio.get("mediaKey") if isinstance(audio, dict) else None)
                    file_path = await whatsapp_service.download_media(audio_url, file_prefix="voice_note", media_key=media_key)
                    # 2. Transcription via le service Whisper
                    from app.services.transcription_service import transcription_service
                    transcribed_text = await transcription_service.transcribe_audio(file_path)
                    if transcribed_text:
                        logger.info(f"🎙️ Note vocale transcrite avec succès pour {phone}: '{transcribed_text}'")
                        text = transcribed_text
                        audio = None  # On vide la variable audio
                    else:
                        logger.warning(f"⚠️ Échec de la transcription de la note vocale pour {phone}.")
                except Exception as e:
                    logger.error(f"❌ Erreur lors de la transcription de la note vocale: {str(e)}")

        # Si c'est un message de type image, on le télécharge et on l'enregistre dans pending_media
        if image:
            # S'assurer qu'un texte est défini pour alerter l'agent, même s'il n'y a pas de caption
            if not text:
                text = "[Image reçue]"
            elif "[Image reçue]" not in text:
                # S'il y a déjà un texte (ex: caption), on ajoute l'indicateur d'image
                text = f"{text}\n[Image reçue]"

            image_url = getattr(image, "url", None) or (image.get("url") if isinstance(image, dict) else None)
            if image_url:
                try:
                    # 1. Téléchargement réel du média image
                    media_key = getattr(image, "mediaKey", None) or (image.get("mediaKey") if isinstance(image, dict) else None)
                    file_path = await whatsapp_service.download_media(image_url, file_prefix="product_image", media_key=media_key)
                    # 2. Enregistrement en base de données
                    async with AsyncSessionLocal() as db:
                        from app.models.pendingMedia import PendingMedia
                        pending = PendingMedia(
                            phone=phone,
                            media_id=media_key or "image",
                            file_path=file_path,
                            media_type="image"
                        )
                        db.add(pending)
                        await db.commit()
                        logger.info(f"💾 Média image {pending.id} téléchargé et mis en attente pour {phone}")
                        # Mettre à jour le texte pour indiquer que l'enregistrement a réussi
                        text = text.replace("[Image reçue]", "[Image reçue et enregistrée]")
                except Exception as e:
                    logger.error(f"❌ Erreur lors de l'enregistrement du média image: {str(e)}")
                    text = text.replace("[Image reçue]", "[Tentative de réception d'image échouée]")


        # Si c'est un message de réponse (reply), on pré-formate le texte cité directement à la fin du texte principal
        quoted_prefix = ""
        if quoted_text:
            quoted_prefix = f"\n\n[Message cité : \"{quoted_text}\"]"
        elif quoted_image:
            quoted_prefix = "\n\n[Message cité : une image a été citée]"
        elif quoted_audio:
            quoted_audio_url = getattr(quoted_audio, "url", None) or (quoted_audio.get("url") if isinstance(quoted_audio, dict) else None)
            if quoted_audio_url:
                try:
                    quoted_media_key = getattr(quoted_audio, "mediaKey", None) or (quoted_audio.get("mediaKey") if isinstance(quoted_audio, dict) else None)
                    quoted_file_path = await whatsapp_service.download_media(quoted_audio_url, file_prefix="quoted_voice_note", media_key=quoted_media_key)
                    from app.services.transcription_service import transcription_service
                    transcribed_quoted_text = await transcription_service.transcribe_audio(quoted_file_path)
                    if transcribed_quoted_text:
                        quoted_prefix = f"\n\n[Message cité (Note vocale) : \"{transcribed_quoted_text}\"]"
                    else:
                        quoted_prefix = "\n\n[Message cité : un enregistrement audio a été cité]"
                except Exception as e:
                    logger.error(f"❌ Erreur lors de la transcription de la note vocale citée: {str(e)}")
                    quoted_prefix = "\n\n[Message cité : un enregistrement audio a été cité]"
            else:
                quoted_prefix = "\n\n[Message cité : un enregistrement audio a été cité]"

        if quoted_prefix:
            text = f"{text or ''}{quoted_prefix}".strip()

        # 1. Vérifier d'abord s'il y a une session active en base locale
        has_active_session = False
        yaburu_data = None
        
        async with AsyncSessionLocal() as db:
            from app.models.stores import store as StoreModel
            from sqlalchemy.orm import selectinload
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
                has_active_session = True

        if not has_active_session:
            # Si aucune session active locale n'est trouvée, passer par la vérification / authentification externe Yaburu
            logger.info(f"ℹ️ Aucune session active locale pour {phone}. Authentification auprès de Yaburu API...")
            from app.services.yaburu_service import yaburu_service
            yaburu_data = await yaburu_service.check_user(phone)
            
            if not yaburu_data:
                logger.warning(f"🚫 Accès refusé pour {phone}. Non trouvé sur Yaburu.")
                await whatsapp_service.send_text_message(phone, "Désolé, votre numéro n'est pas associé à un compte Yaburu actif. Veuillez contacter le support si c'est une erreur.")
                return "ACCESS_DENIED"

        async with AsyncSessionLocal() as db:
            user = None
            if not has_active_session:
                # 2. Synchroniser ou créer l'utilisateur et ses boutiques uniquement si pas de session active
                user = await onboarding_service.handle_user_connection(db, phone, yaburu_data)
            else:
                # Récupérer l'utilisateur existant en base locale
                user_res = await db.execute(select(User).where(User.telephone == phone))
                user = user_res.scalar_one_or_none()
                
            if not user:
                logger.error(f"❌ Utilisateur introuvable en base pour le numéro {phone}.")
                return "ERROR"
            
            # 3. Enregistrer le prompt dans la file d'attente
            queued_msg = MessageQueue(phone=phone, text=text)
            db.add(queued_msg)
            await db.commit()
            
            # 4. Vérifier si un traitement est déjà actif pour cet utilisateur (en DB ou en mémoire)
            from app.services.queue_processor import active_processors
            if user.traitement_en_cours or phone in active_processors:
                logger.info(f"📥 [QUEUE] Un traitement est déjà actif pour {phone}. Message ajouté à la file d'attente.")
                return "QUEUED"
            
            # Sinon, on marque IMMÉDIATEMENT en mémoire ET en DB
            # IMPORTANT: ajouter à active_processors AVANT le commit DB et AVANT create_task
            # pour éviter la race condition si un 2ème webhook arrive dans le micro-délai.
            active_processors.add(phone)
            user.traitement_en_cours = True
            await db.commit()

        # Mettre en cache les données Yaburu déjà récupérées pour éviter un 2ème appel HTTP dans queue_processor
        if yaburu_data:
            yaburu_data_cache[phone] = yaburu_data

        # 5. Lancer le processeur de file asynchrone en arrière-plan
        from app.services.queue_processor import process_user_queue
        asyncio.create_task(process_user_queue(phone))
        logger.info(f"🚀 [QUEUE] Lancement du processeur asynchrone pour {phone}.")
        return "PROCESSING_STARTED"

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
