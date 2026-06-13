import logging
import asyncio
from datetime import datetime
from typing import Optional, Any, Dict
from sqlalchemy import select, and_
from app.db import AsyncSessionLocal
from app.models.user import User
from app.models.sessions import Session
from app.models.messageQueue import MessageQueue
from app.services.onboarding_service import onboarding_service
from app.services.agent_dispatcher import agent_dispatcher
from app.services.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)

# Cache en mémoire : évite de rappeler check_user dans queue_processor
yaburu_data_cache: Dict[str, Any] = {}

# Cache des sessions actives (ultra-rapide, évite de requêter PostgreSQL à chaque message)
active_session_cache: Dict[str, dict] = {}

class WebhookRouter:
    
    async def route_message(self, phone: str, text: Optional[str] = None, audio: Optional[Any] = None, image: Optional[Any] = None, quoted_text: Optional[str] = None, quoted_image: Optional[Any] = None, quoted_audio: Optional[Any] = None):
        import time
        from app.services.queue_processor import last_activity, pending_messages, active_processors, in_flight_requests
        
        start_t = time.time()
        
        # 1. Mise à jour immédiate du chrono anti-rebond dès la réception réseau
        # Cela empêche le queue_processor d'un message précédent de démarrer s'il est en train de patienter
        last_activity[phone] = time.time()
        
        # 2. Indiquer qu'une requête est en cours de préparation (suspend le debounce)
        in_flight_requests[phone] = in_flight_requests.get(phone, 0) + 1
        
        try:
            # Feedback visuel instantané ("En train d'écrire...")
            asyncio.create_task(whatsapp_service.send_typing(phone))

            # --- TRAITEMENT DES MÉDIAS ---
            if audio:
                audio_url = getattr(audio, "url", None) or (audio.get("url") if isinstance(audio, dict) else None)
                if audio_url:
                    try:
                        media_key = getattr(audio, "mediaKey", None) or (audio.get("mediaKey") if isinstance(audio, dict) else None)
                        file_path = await whatsapp_service.download_media(audio_url, file_prefix="voice_note", media_key=media_key)
                        from app.services.transcription_service import transcription_service
                        transcribed_text = await transcription_service.transcribe_audio(file_path)
                        if transcribed_text:
                            logger.info(f"🎙️ Note vocale transcrite avec succès pour {phone}: '{transcribed_text}'")
                            text = transcribed_text
                            audio = None
                        else:
                            logger.warning(f"⚠️ Échec de la transcription de la note vocale pour {phone}.")
                    except Exception as e:
                        logger.error(f"❌ Erreur lors de la transcription de la note vocale: {str(e)}")

            if image:
                if not text:
                    text = "[Image reçue]"
                elif "[Image reçue]" not in text:
                    text = f"{text}\n[Image reçue]"

                image_url = getattr(image, "url", None) or (image.get("url") if isinstance(image, dict) else None)
                if image_url:
                    try:
                        media_key = getattr(image, "mediaKey", None) or (image.get("mediaKey") if isinstance(image, dict) else None)
                        file_path = await whatsapp_service.download_media(image_url, file_prefix="product_image", media_key=media_key)
                        logger.info(f"💾 Média image téléchargé pour {phone} au chemin {file_path}")
                        text = text.replace("[Image reçue]", f"[Image reçue et enregistrée. Chemin_local: {file_path}]")
                    except Exception as e:
                        logger.error(f"❌ Erreur lors du téléchargement de l'image: {str(e)}")
                        text = text.replace("[Image reçue]", "[Tentative de réception d'image échouée]")

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

            # --- VÉRIFICATION BASE DE DONNÉES ---
            has_active_session = False
            yaburu_data = None
            
            cached_session = active_session_cache.get(phone)
            if cached_session and cached_session.get("expires_at", 0) > datetime.utcnow().timestamp():
                has_active_session = True
                logger.info(f"⚡ [CACHE HIT] Session active trouvée en mémoire RAM pour {phone}.")
            else:
                t0 = time.time()
                async with AsyncSessionLocal() as db:
                    session_result = await db.execute(
                        select(Session)
                        .join(User, Session.utilisateur_id == User.id)
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
                        active_session_cache[phone] = {
                            "expires_at": active_sessions[0].expire_le.timestamp()
                        }
                logger.info(f"⏱️ DB Check Session took: {time.time()-t0:.2f}s")

            if not has_active_session:
                logger.info(f"ℹ️ Aucune session active locale pour {phone}. Authentification auprès de Yaburu API...")
                from app.services.yaburu_service import yaburu_service
                t0 = time.time()
                yaburu_data = await yaburu_service.check_user(phone)
                logger.info(f"⏱️ Yaburu API took: {time.time()-t0:.2f}s")
                
                if not yaburu_data:
                    logger.warning(f"🚫 Accès refusé pour {phone}. Non trouvé sur Yaburu.")
                    await whatsapp_service.send_text_message(phone, "Désolé, votre numéro n'est pas associé à un compte Yaburu actif. Veuillez contacter le support si c'est une erreur.")
                    return "ACCESS_DENIED"

            t0 = time.time()
            async with AsyncSessionLocal() as db:
                user = None
                if not has_active_session:
                    user = await onboarding_service.handle_user_connection(db, phone, yaburu_data)
                else:
                    user_res = await db.execute(select(User).where(User.telephone == phone))
                    user = user_res.scalar_one_or_none()
                    
                if not user:
                    logger.error(f"❌ Utilisateur introuvable en base pour le numéro {phone}.")
                    return "ERROR"

                # --- MUTEX ET FILE D'ATTENTE ---
                
                # 2. Enregistrer le prompt final dans la file d'attente RAM
                if phone not in pending_messages:
                    pending_messages[phone] = []
                if text:
                    pending_messages[phone].append(text)
                    
                # 3. Réinitialiser le timer anti-rebond avec l'heure de FIN de traitement
                # Garantit que la queue attendra bien 1.5s à partir de maintenant.
                last_activity[phone] = time.time()
                
                # 4. Vérifier si un traitement est déjà actif EN MÉMOIRE (Mutex RAM)
                if phone in active_processors:
                    logger.info(f"📥 [QUEUE] Un traitement est déjà actif pour {phone}. Message ajouté à la file d'attente.")
                    return "QUEUED"
                
                # Sinon, on verrouille IMMÉDIATEMENT en mémoire
                active_processors.add(phone)
                
                try:
                    # Mise à jour DB uniquement à titre d'information / UI
                    user.traitement_en_cours = True
                    await db.commit()
                    logger.info(f"⏱️ DB Insert/Commit took: {time.time()-t0:.2f}s")

                    if yaburu_data:
                        yaburu_data_cache[phone] = yaburu_data

                    # 5. Lancer le processeur de file asynchrone en arrière-plan
                    from app.services.queue_processor import process_user_queue
                    asyncio.create_task(process_user_queue(phone))
                    logger.info(f"🚀 [QUEUE] Lancement du processeur asynchrone pour {phone}. (Total Webhook: {time.time()-start_t:.2f}s)")
                    return "PROCESSING_STARTED"
                    
                except Exception as e:
                    # En cas d'erreur critique dans la préparation, on libère le verrou mémoire
                    active_processors.discard(phone)
                    logger.exception("❌ Erreur dans la préparation du routage")
                    raise e
                    
        finally:
            # Libérer la requête en vol, quoi qu'il arrive
            in_flight_requests[phone] -= 1
            if in_flight_requests[phone] < 0:
                in_flight_requests[phone] = 0

webhook_router = WebhookRouter()
