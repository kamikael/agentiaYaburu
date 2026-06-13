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
        Gère la suite de l'onboarding. Puisque l'agent est omniscient, on ne demande plus
        de choisir une boutique. On crée/renouvelle directement la session globale de l'utilisateur.
        """
        # Récupérer les boutiques de l'utilisateur
        store_res = await db.execute(select(StoreModel).where(StoreModel.user_id == user.id).order_by(StoreModel.created_at.asc()))
        stores = store_res.scalars().all()
        
        if not stores:
            await whatsapp_service.send_text_message(phone, "Vous n'avez aucune boutique active sur Yaburu. Veuillez en créer une avant d'utiliser l'assistant.")
            return "ONBOARDING_NO_stores"

        # Connexion automatique globale
        await self._create_or_renew_session(db, user.id)
        user.onboarding_step = "completed"
        await db.commit()
        
        # Message de bienvenue
        welcome_msg = f"Bienvenue {user.first_name or ''} ! Je suis votre assistant Yaburu. Je vois que vous gérez {len(stores)} boutique(s). Comment puis-je vous aider aujourd'hui ?"
        await whatsapp_service.send_text_message(phone, welcome_msg)
        
        # Message 2 : Menu des capacités
        import asyncio
        await asyncio.sleep(1)
        from app.agent.capabilities_menu import CAPABILITIES_MENU
        await whatsapp_service.send_text_message(phone, CAPABILITIES_MENU)
        
        return "ONBOARDING_COMPLETED"

    async def _create_or_renew_session(self, db: AsyncSession, user_id: Any):
        """Crée ou renouvelle la session globale pour un utilisateur, avec une validité de 24h"""
        import secrets
        new_token = secrets.token_urlsafe(32)
        new_expiration = datetime.utcnow() + timedelta(hours=24)
        
        # Chercher s'il y a déjà une session pour cet utilisateur
        res = await db.execute(select(Session).where(Session.utilisateur_id == user_id))
        existing_session = res.scalar_one_or_none()
        
        if existing_session:
            # Renouvellement : UPDATE
            existing_session.session_token = new_token
            existing_session.est_active = True
            existing_session.expire_le = new_expiration
            logger.info(f"🔄 Session globale renouvelée pour l'utilisateur {user_id}")
            return existing_session
        else:
            # Création : INSERT
            new_session = Session(
                utilisateur_id=user_id,
                session_token=new_token,
                est_active=True,
                expire_le=new_expiration
            )
            db.add(new_session)
            await db.flush()
            logger.info(f"🆕 Nouvelle session globale créée pour l'utilisateur {user_id}")
            return new_session

onboarding_service = OnboardingService()
