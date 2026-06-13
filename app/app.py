import hmac
import hashlib
import logging
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from app.schemas.webhook import Payload
import json
from app.services.webhook_router import webhook_router
from app.api import admin_rag
from config import settings 


# Configuration du logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Yaburu ChatBot API")

# Configurer le CORS pour autoriser le frontend React local (Vite utilise souvent 5173 ou 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure le routeur Admin RAG
app.include_router(admin_rag.router, prefix="/api/v1/admin/rag", tags=["Admin RAG"])

# Configuration (Devrait être dans config.py ou .env)
VERIFY_TOKEN = settings.WHATSAPP_API_TOKEN
WHATSAPP_APP_SECRET = settings.WHATSAPP_SECRET

# =========================
# Health check
# =========================
@app.get("/health")
def health():
    return {"status": "ok", "message": "Yaburu API est opérationnelle"}

# =========================
# Vérification webhook (Meta)
# =========================
@app.get("/api/v1/webhooks/whatsapp")
async def verify_webhook_endpoint(
    request: Request
):
    """
    Endpoint pour la vérification initiale de Meta (GET).
    """
    params = request.query_params
    hub_mode = params.get("hub.mode")
    hub_challenge = params.get("hub.challenge")
    hub_verify_token = params.get("hub.verify_token")

    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("✅ Webhook vérifié par Meta")
        return PlainTextResponse(content=hub_challenge)
    
    logger.warning("❌ Échec de vérification du webhook")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

# =========================
# Réception messages WhatsApp
# =========================
def verify_whatsapp_signature(request_body: bytes, signature_header: str) -> bool:
    """Valide la signature HMAC SHA256 de Meta"""
    if not signature_header:
        return False
    
    try:
        # Format: sha256=hash
        received_hash = signature_header.split("=")[1]
        expected_hash = hmac.new(
            WHATSAPP_APP_SECRET.encode(),
            request_body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_hash, received_hash)
    except Exception:
        return False

@app.post("/api/v1/webhooks/whatsapp")
#https://glazing-squishier-talisman.ngrok-free.dev/api/v1/webhooks/whatsapp
async def receive_webhook(request: Request):
    """
    Réception des événements WhatsApp (POST)
    """
    
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    request_body = await request.body()

    # Validation signature (optionnel)
    # if WHATSAPP_APP_SECRET != "votre_secret_app_meta":
    #     if not verify_whatsapp_signature(request_body, signature_header):
    #         logger.error("❌ Signature invalide")
    #         raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        body_json = json.loads(request_body)

        # Validation Pydantic avec tes schémas
        payload = Payload(**body_json)

    except Exception as e:
        logger.error(f"❌ Erreur parsing Webhook: {str(e)}")

        # IMPORTANT:
        # WhatsApp renvoie le webhook si on répond autre chose que 200
        return {
            "status": "error",
            "message": "Invalid payload format"
        }

    try:
        message_data = payload.data.messages
        if not message_data or not message_data.key:
            return {"status": "ok", "message": "No active message data"}

        if message_data.key.fromMe:
            logger.info("⏭️ Message ignoré : message sortant (fromMe = True)")
            return {"status": "ok", "message": "Ignored outgoing message"}

        phone = message_data.key.cleanedSenderPn
        message = message_data.message

        text = None
        audio = None
        image = None

        quoted_text = None
        quoted_image = None
        quoted_audio = None

        # =========================
        # MESSAGE TEXTE
        # Priorité : extendedTextMessage > conversation > messageBody
        # =========================
        if hasattr(message, "extendedTextMessage") and message.extendedTextMessage:
            text = message.extendedTextMessage.text
        elif hasattr(message, "conversation") and message.conversation:
            text = message.conversation
        
        # Fallback sur messageBody (champ de premier message ou cas particulier)
        if not text and message_data.messageBody:
            text = message_data.messageBody

        # =========================
        # MESSAGE AUDIO
        # =========================
        if hasattr(message, "audioMessage") and message.audioMessage:
            audio = message.audioMessage

        # =========================
        # MESSAGE IMAGE
        # =========================
        if hasattr(message, "imageMessage") and message.imageMessage:
            image = message.imageMessage
            # Extraire la légende (caption) de l'image s'il y en a une et qu'aucun texte n'est défini
            if not text and hasattr(image, "caption") and image.caption:
                text = image.caption

        # =========================
        # CONTEXT INFO (reply)
        # =========================
        context = (
            getattr(
                getattr(message, "extendedTextMessage", None),
                "contextInfo",
                None
            )
            or getattr(
                getattr(message, "imageMessage", None),
                "contextInfo",
                None
            )
            or getattr(
                getattr(message, "audioMessage", None),
                "contextInfo",
                None
            )
            or getattr(
                getattr(message, "videoMessage", None),
                "contextInfo",
                None
            )
        )

        # =========================
        # MESSAGE REPLY
        # =========================
        if context and hasattr(context, "quotedMessage"):

            quoted_message = context.quotedMessage

            # Réponse à un texte simple
            if hasattr(quoted_message, "conversation"):
                quoted_text = quoted_message.conversation

            # Réponse à un extendedTextMessage
            elif (
                hasattr(quoted_message, "extendedTextMessage")
                and quoted_message.extendedTextMessage
            ):
                quoted_text = quoted_message.extendedTextMessage.text

            # Réponse à une image
            elif hasattr(quoted_message, "imageMessage"):
                quoted_image = quoted_message.imageMessage

            # Réponse à un audio
            elif hasattr(quoted_message, "audioMessage"):
                quoted_audio = quoted_message.audioMessage

        logger.info(
            f"""
📩 Nouveau message WhatsApp
👤 Téléphone : {phone}
💬 Texte : {text}
🎵 Audio : {'Oui' if audio else 'Non'}
🖼️ Image : {'Oui' if image else 'Non'}

↩️ Réponse texte : {quoted_text}
🖼️ Réponse image : {'Oui' if quoted_image else 'Non'}
🎵 Réponse audio : {'Oui' if quoted_audio else 'Non'}
"""
        )

        import asyncio
        # Lancement de la routine de routage et de base de données en arrière-plan
        # Cela permet au serveur de répondre 200 OK à WhatsApp immédiatement (< 50ms)
        asyncio.create_task(
            webhook_router.route_message(
                phone=phone,
                text=text,
                audio=audio,
                image=image,
                quoted_text=quoted_text,
                quoted_image=quoted_image,
                quoted_audio=quoted_audio
            )
        )

    except Exception as e:
        logger.exception(f"❌ Erreur traitement message:")

    return {"status": "ok"}

