import logging
from typing import Optional, List
from app.agent.service import agent_service
from app.services.whatsapp_service import whatsapp_service
from app.agent.capabilities_menu import CAPABILITIES_MENU, is_menu_requested, is_intermediate_response
from app.models.sessions import Session

logger = logging.getLogger(__name__)

class AgentDispatcher:
    """
    Service chargé de coordonner l'appel à l'agent et l'envoi de la réponse via WhatsApp.
    """

    async def handle_agent_message(self, session: Session, phone: str, text: str, conversation_id: str, user_id: str, image: Optional[dict] = None, is_first_message: bool = False):
        """
        Traite un message utilisateur via l'agent IA.
        """
        # Vérifier si le marchand demande explicitement le menu
        user_wants_menu = is_menu_requested(text) if text else False

        # 1. Obtenir la réponse de l'agent
        response_text = await agent_service.get_response(
            user_id=user_id,
            conversation_id=conversation_id,
            text=text,
            phone=phone,
            image=image,
        )
        
        # 2. Ajouter le menu UNIQUEMENT si le marchand le demande explicitement
        #    ("menu", "aide", "help", "que peux-tu faire", etc.)
        #    Le menu de première connexion est déjà géré par l'onboarding_service.
        #    Sauf si la réponse est une étape intermédiaire (attente photo, choix boutique)
        if user_wants_menu and not is_intermediate_response(response_text):
            response_text = response_text + "\n\n" + CAPABILITIES_MENU

        # 3. Envoyer la réponse via WhatsApp
        await whatsapp_service.send_text_message(phone, response_text)

agent_dispatcher = AgentDispatcher()
