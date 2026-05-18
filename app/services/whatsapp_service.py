import logging
import json
from typing import List, Optional, Dict, Any
from app.schemas.webhook import SendMessageRequest, MessageType, OutboundTextMessage, OutboundInteractiveMessage

logger = logging.getLogger(__name__)

class WhatsAppService:
    
    """
    Service pour envoyer des messages via l'API WhatsApp de Meta.
    Actuellement en mode simulation.
    """
    
    async def send_text_message(self, to: str, body: str) -> bool:
        """Envoie un message texte simple"""
        payload = SendMessageRequest(
            to=to,
            type=MessageType.TEXT,
            text=OutboundTextMessage(body=body)
        )
        return await self._send(payload)

    async def send_store_selection(self, to: str, stores: List[Dict[str, Any]]) -> bool:
        """Envoie un message texte listant les boutiques pour choix manuel"""
        
        store_list_text = "Plusieurs boutiques sont associées à votre compte. Sur laquelle souhaitez-vous travailler ?\n\n"
        store_list_text += "Répondez avec le *numéro* ou le *nom exact* de la boutique :\n\n"
        
        for i, store in enumerate(stores, 1):
            store_list_text += f"{i}. *{store['store_name']}*\n"

        return await self.send_text_message(to, store_list_text)

    async def get_media_url(self, media_id: str) -> str:
        """Simule la récupération de l'URL d'un média via l'API Meta"""
        return f"https://whatsapp.media.simulation/{media_id}.jpg"

    async def download_media(self, media_id: str) -> str:
        """Simule le téléchargement d'un média et retourne son chemin local"""
        # En mode simulation, on crée juste un nom de fichier fictif
        import os
        fake_path = f"tmp/media_{media_id}.jpg"
        logger.info(f"📥 [WHATSAPP MEDIA] Téléchargement simulé de {media_id} vers {fake_path}")
        return fake_path

    async def _send(self, payload: SendMessageRequest) -> bool:
        """
        Log le payload JSON pour simuler l'envoi.
        Plus tard, cette méthode fera un POST sur l'API Meta.
        """
        json_payload = payload.json(exclude_none=True, by_alias=True)
        logger.info(f"📤 [WHATSAPP OUTBOUND] Envoi vers {payload.to}: {json_payload}")
        
        # On affiche aussi un message "humain" pour le debug
        if payload.type == MessageType.TEXT:
            print(f"\n[BOT -> {payload.to}]: {payload.text.body}\n")
        elif payload.type == MessageType.INTERACTIVE:
            print(f"\n[BOT -> {payload.to}]: INTERACTIF ({payload.interactive.type}) - {payload.interactive.body['text']}\n")
            
        return True

whatsapp_service = WhatsAppService()
