import logging
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.models.user import User
from app.models.stores import store as StoreModel
from app.models.sessions import Session
from app.services.yaburu_service import yaburu_service
from app.services.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)    

class OnboardingService:
    """
    Gère le flux d'identification et d'onboarding des utilisateurs WhatsApp.
    """

    async def handle_user_connection(self, db: AsyncSession, phone: str, yaburu_data: Dict[str, Any]) -> User:
        """
        Synchronise les données de l'utilisateur et de ses boutiques depuis Yaburu.
        Crée l'utilisateur localement s'il n'existe pas.
        """
        y_user = yaburu_data.get("user", {})
        y_stores = yaburu_data.get("stores", [])
        
        # 1. Rechercher ou créer l'utilisateur
        result = await db.execute(select(User).where(User.phone_number == phone))
        user = result.scalar_one_or_none()
        
        if not user:
            logger.info(f"🆕 Création d'un nouvel utilisateur local pour {phone}")
            user = User(phone_number=phone)
            db.add(user)
            await db.flush() # Pour avoir l'ID
        
        # 2. Mettre à jour les infos profil
        user.first_name = y_user.get("firstname") or y_user.get("name")
        user.last_name = y_user.get("lastname")
        user.email = y_user.get("email") # L'email vient maintenant du backend Yaburu
        
        # 3. Synchroniser les boutiques
        for s_data in y_stores:
            y_store_id = str(s_data.get("id"))
            store_res = await db.execute(select(StoreModel).where(StoreModel.yaburu_store_id == y_store_id))
            store = store_res.scalar_one_or_none()
            
            if not store:
                logger.info(f"🏪 Ajout de la boutique {s_data.get('name')} pour {phone}")
                store = StoreModel(
                    user_id=user.id,
                    yaburu_store_id=y_store_id,
                    store_name=s_data.get("name"),
                    store_url=s_data.get("domaine")
                )
                db.add(store)
            else:
                # Mise à jour au cas où le nom aurait changé
                store.store_name = s_data.get("name") or s_data.get("name")
                store.store_url = s_data.get("domaine")
        
        await db.commit()
        await db.refresh(user)
        return user

    async def process_onboarding_step(self, db: AsyncSession, user: User, phone: str, text: Optional[str] = None, interactive_id: Optional[str] = None):
        """
        Gère la suite de l'onboarding (choix de boutique si pas de session).
        """
        # Récupérer les boutiques de l'utilisateur
        store_res = await db.execute(select(StoreModel).where(StoreModel.user_id == user.id).order_by(StoreModel.created_at.asc()))
        stores = store_res.scalars().all()
        
        if not stores:
            await whatsapp_service.send_text_message(phone, "Vous n'avez aucune boutique active sur Yaburu. Veuillez en créer une avant d'utiliser l'assistant.")
            return "ONBOARDING_NO_stores"

        # Cas 1 : Une seule boutique -> Connexion automatique
        if len(stores) == 1:
            store = stores[0]
            await self._create_session(db, user.id, store.id)
            user.onboarding_step = "completed"
            await db.commit()
            
            # Message de bienvenue
            welcome_msg = f"Bienvenue {user.first_name or ''} ! Votre boutique *{store.store_name}* est maintenant connectée. Comment puis-je vous aider ?"
            await whatsapp_service.send_text_message(phone, welcome_msg)
            return "ONBOARDING_COMPLETED"

        # Cas 2 : Plusieurs boutiques
        step = (user.onboarding_step or "waiting_for_store").lower()

        if step == "waiting_for_store":
            # Si on vient d'arriver ou si le texte est vide, on envoie la liste
            if not text:
                stores_data = [{"id": s.yaburu_store_id, "store_name": s.store_name} for s in stores]
                await whatsapp_service.send_store_selection(phone, stores_data)
                return "ONBOARDING_WAITING_store"
            
            # Analyse de la réponse (Numéro ou Nom)
            input_text = text.strip()
            selected_store = None
            
            # Test si c'est un numéro (1, 2, 3...)
            if input_text.isdigit():
                idx = int(input_text) - 1
                if 0 <= idx < len(stores):
                    selected_store = stores[idx]
            
            # Sinon test si c'est le nom exact
            if not selected_store:
                for s in stores:
                    if s.store_name.lower() == input_text.lower():
                        selected_store = s
                        break
            
            if selected_store:
                await self._create_session(db, user.id, selected_store.id)
                user.onboarding_step = "completed"
                await db.commit()
                await whatsapp_service.send_text_message(phone, f"Parfait ! Vous êtes maintenant connecté à *{selected_store.store_name}*. Que souhaitez-vous faire ?")
                return "ONBOARDING_COMPLETED"
            else:
                # Entrée invalide -> Rappel des consignes
                error_msg = "⚠️ Choix non reconnu. Veuillez répondre par le *numéro* (ex: 1) ou le *nom exact* de la boutique listée ci-dessus."
                await whatsapp_service.send_text_message(phone, error_msg)
                
                # On renvoie la liste pour plus de clarté
                stores_data = [{"id": s.yaburu_store_id, "store_name": s.store_name} for s in stores]
                await whatsapp_service.send_store_selection(phone, stores_data)
                return "ONBOARDING_CONTINUE"

        # Par défaut, on renvoie la liste si on est bloqué
        user.onboarding_step = "waiting_for_store"
        await db.commit()
        stores_data = [{"id": s.yaburu_store_id, "store_name": s.store_name} for s in stores]
        await whatsapp_service.send_store_selection(phone, stores_data)
        return "ONBOARDING_CONTINUE"

    async def _create_session(self, db: AsyncSession, user_id: Any, store_id: Any):
        """Crée une session active de 24h"""
        import secrets
        token = secrets.token_urlsafe(32)
        
        # Désactiver les anciennes sessions
        await db.execute(
            Session.__table__.update()
            .where(Session.user_id == user_id)
            .values(is_active=False)
        )
        
        new_session = Session(
            user_id=user_id,
            store_id=store_id,
            session_token=token,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        db.add(new_session)

onboarding_service = OnboardingService()
