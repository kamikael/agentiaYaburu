import logging
from typing import Optional
from app.agent.service import agent_service
from app.services.whatsapp_service import whatsapp_service
from app.models.sessions import Session

logger = logging.getLogger(__name__)

class AgentDispatcher:
    """
    Service chargé de coordonner l'appel à l'agent et l'envoi de la réponse via WhatsApp.
    """

    async def handle_agent_message(self, session: Session, phone: str, text: str, conversation_id: str):
        """
        Traite un message utilisateur via l'agent IA.
        """
        # 1. Obtenir la réponse de l'agent
        response_text = await agent_service.get_response(
            user_id=str(session.user_id),
            store_id=str(session.store_id),
            conversation_id=conversation_id,
            text=text,
            phone=phone
        )
        
        # 2. Envoyer la réponse via WhatsApp (Simulation console pour l'instant)
        await whatsapp_service.send_text_message(phone, response_text)

agent_dispatcher = AgentDispatcher()
