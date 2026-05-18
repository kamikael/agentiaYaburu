import hmac
import hashlib
import logging
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from app.schemas.webhook import WebhookPayload, MessageType
from app.services.webhook_router import webhook_router
from config import settings 


# Configuration du logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Yaburu ChatBot API")

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
async def receive_webhook(request: Request):
    """
    Réception des événements WhatsApp (POST).
    """
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    request_body = await request.body()
    
    # Validation de signature (désactivée en dev local si pas de secret)
    # if WHATSAPP_APP_SECRET != "votre_secret_app_meta":
    #    if not verify_whatsapp_signature(request_body, signature_header):
    #        logger.error("❌ Signature invalide")
    #        raise HTTPException(status_code=403, detail="Invalid signature")
    
    try:
        body_json = json.loads(request_body)
        payload = WebhookPayload(**body_json)
    except Exception as e:
        logger.error(f"❌ Erreur parsing Webhook: {str(e)}")
        # On retourne 200 quand même pour éviter que Meta ne renvoie sans cesse le même message
        return {"status": "error", "message": "Invalid payload format"}

    # Parcours des entrées et messages
    for entry in payload.entry:
        for change in entry.changes:
            value = change.value
            if value.messages:
                for message in value.messages:
                    phone = message.from_
                    text = None
                    interactive_id = None
                    
                    if message.type == MessageType.TEXT and message.text:
                        text = message.text.body
                    elif message.type == MessageType.IMAGE and message.image:
                        # Capture de l'image pour le tampon
                        await webhook_router.handle_media_message(phone, message.image.id, "image")
                        text = message.image.caption or "[Image reçue]"
                    elif message.type == MessageType.INTERACTIVE and message.interactive:
                        if message.interactive.button_reply:
                            interactive_id = message.interactive.button_reply.id
                        elif message.interactive.list_reply:
                            interactive_id = message.interactive.list_reply.id
                    
                    # Routage intelligent (Onboarding ou Agent IA)
                    logger.info(f"📩 Message reçu de {phone}: {text or interactive_id}")
                    await webhook_router.route_message(
                        phone=phone,
                        text=text,
                        interactive_id=interactive_id
                    )

    return {"status": "ok"}