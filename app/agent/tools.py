import json
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from app.services.yaburu_service import yaburu_service # On importe l'instance directement
from app.agent.context import store_id_ctx

from sqlalchemy import select, delete, and_
from app.db import AsyncSessionLocal
from app.models.pendingMedia import PendingMedia
from app.models.user import User
from app.models.stores import store as StoreModel
from app.models.sessions import Session
from app.agent.context import store_id_ctx, phone_number_ctx, yaburu_store_id_ctx
from datetime import datetime, timedelta
import secrets

logger = logging.getLogger(__name__)

class FinalAnswer(BaseModel):
    """Réponse finale structurée à envoyer à l'utilisateur."""
    answer: str = Field(description="La réponse textuelle claire et concise pour le marchand.")
    stats_included: bool = Field(default=False, description="Indique si des statistiques ont été incluses dans la réponse.")

@tool
async def get_store_stats() -> str:
    """Récupère les statistiques complètes de votre boutique (produits, ventes, clients, revenus)."""
    store_id = yaburu_store_id_ctx.get()
    if not store_id:
        return "Erreur : Aucun contexte de boutique trouvé."
    try:
        stats = await yaburu_service.get_store_stats(store_id)
        if not stats:
            return "Aucune statistique disponible pour le moment."
        return json.dumps(stats, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in get_store_stats tool: {e}")
        return f"Erreur lors de la récupération des statistiques: {str(e)}"

@tool
async def get_store_users() -> str:
    """récupère les données de l'utilisateurs ainsi que l'ensemble de boutique qu'il possède"""
    phone = phone_number_ctx.get()
    if not phone:
        return "Erreur : Aucun contexte de téléphone trouvé."
    try:
        data = await yaburu_service.check_user(phone)
        if not data:
            return "Aucune information disponible pour le moment."
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in  get_store_users tool: {e}")
        return f"Erreur lors de la récupération des données de l'utilisateur: {str(e)}"

@tool
async def get_store_orders() -> str:
    """Récupère la liste complète des commandes passées dans votre boutique."""
    store_id = yaburu_store_id_ctx.get()
    if not store_id:
        return "Erreur : Aucun contexte de boutique trouvé."
    try:
        orders = await yaburu_service.get_store_orders(store_id)
        if not orders:
            return "Aucune commande trouvée."
        return json.dumps(orders, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in get_store_orders tool: {e}")
        return f"Erreur lors de la récupération des commandes: {str(e)}"

@tool
async def get_store_products() -> str:
    """Récupère la liste de tous les produits disponibles dans votre boutique."""
    store_id = yaburu_store_id_ctx.get()
    if not store_id:
        return "Erreur : Aucun contexte de boutique trouvé."

    try:
        products = await yaburu_service.get_store_products(store_id)
        if not products:
            return "Aucun produit trouvé."
        return json.dumps(products, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in get_store_products tool: {e}")
        return f"Erreur lors de la récupération des produits: {str(e)}"

class ChangeStoreSchema(BaseModel):
    name_store: str = Field(..., description="Le nom exact de la boutique vers laquelle pivoter.")

@tool(args_schema=ChangeStoreSchema)
async def change_store(name_store: str) -> str:
    """Permet de basculer la session de travail active vers la boutique spécifiée par son nom."""
    phone = phone_number_ctx.get()
    if not phone:
        return "Erreur : Aucun contexte de numéro de téléphone trouvé."

    try:
        # 1. Interroger Yaburu pour valider la boutique
        data = await yaburu_service.check_user(phone)
        if not data or "stores" not in data:
            return "Erreur : Impossible de récupérer vos boutiques depuis Yaburu."

        stores = data["stores"]
        target_remote_store = None
        cleaned_input = name_store.strip().lower()

        # Recherche insensible à la casse
        for s in stores:
            if s.get("name", "").strip().lower() == cleaned_input:
                target_remote_store = s
                break

        if not target_remote_store:
            return f"Erreur : Aucune boutique trouvée avec le nom '{name_store}'."

        target_yaburu_store_id = str(target_remote_store.get("id"))

        async with AsyncSessionLocal() as db:
            # 2. Récupérer l'utilisateur
            user_res = await db.execute(select(User).where(User.phone_number == phone))
            user = user_res.scalar_one_or_none()
            if not user:
                return "Erreur : Utilisateur local introuvable."

            # 3. Récupérer la boutique locale pré-synchronisée
            store_res = await db.execute(
                select(StoreModel).where(
                    and_(
                        StoreModel.user_id == user.id,
                        StoreModel.yaburu_store_id == target_yaburu_store_id
                    )
                )
            )
            store_obj = store_res.scalar_one_or_none()
            if not store_obj:
                return f"Erreur : La boutique '{name_store}' n'est pas synchronisée localement."

            # 4. Rechercher s'il existe déjà une session valide pour la boutique cible
            existing_session_res = await db.execute(
                select(Session).where(
                    and_(
                        Session.user_id == user.id,
                        Session.store_id == store_obj.id,
                        Session.expires_at > datetime.utcnow()
                    )
                ).order_by(Session.created_at.desc()).limit(1)
            )
            target_sess = existing_session_res.scalars().first()

            # Désactiver TOUTES les sessions actives actuelles de l'utilisateur
            await db.execute(
                Session.__table__.update()
                .where(and_(Session.user_id == user.id, Session.is_active == True))
                .values(is_active=False)
            )

            if target_sess:
                # Si une session valide existe déjà pour cette boutique, on la réactive
                logger.info(f"🔄 Réactivation de la session existante {target_sess.id} pour la boutique {store_obj.store_name}")
                target_sess.is_active = True
            else:
                # Sinon, on crée une nouvelle session active de 24h
                logger.info(f"🆕 Création d'une nouvelle session pour la boutique {store_obj.store_name}")
                token = secrets.token_urlsafe(32)
                target_sess = Session(
                    user_id=user.id,
                    store_id=store_obj.id,
                    session_token=token,
                    is_active=True,
                    expires_at=datetime.utcnow() + timedelta(hours=24)
                )
                db.add(target_sess)

            await db.commit()

            # 5. Mettre à jour les ContextVars pour le tour de réflexion actuel
            yaburu_store_id_ctx.set(target_yaburu_store_id)
            store_id_ctx.set(str(store_obj.id))

            logger.info(f"🔄 Pivotement réussi pour {phone} vers '{store_obj.store_name}'")
            return f"Succès ! Vous avez pivoté avec succès vers la boutique '{store_obj.store_name}'."

    except Exception as e:
        logger.error(f"❌ Erreur lors du change_store : {e}")
        return f"Une erreur technique est survenue : {str(e)}"


class CreateProductSchema(BaseModel):
    name: str = Field(..., description="Le nom du nouveau produit.")
    price: float = Field(..., description="Le prix de vente du produit.")
    stock: int = Field(..., description="La quantité initiale en stock.")
    description: Optional[str] = Field(None, description="Une description optionnelle du produit.")

@tool(args_schema=CreateProductSchema)
async def create_store_product(name: str, price: float, stock: int, description: Optional[str] = None) -> str:
    """
    Crée un nouveau produit dans la boutique. 
    Les images précédemment envoyées par l'utilisateur seront automatiquement rattachées au produit.
    """
    store_id = yaburu_store_id_ctx.get()
    phone = phone_number_ctx.get()
    
    if not store_id or not phone:
        return "Erreur : Contexte manquant (store_id ou phone)."

    try:
        async with AsyncSessionLocal() as db:
            # 1. Récupérer les images en attente pour cet utilisateur
            media_res = await db.execute(
                select(PendingMedia).where(PendingMedia.phone == phone)
            )
            media_list = media_res.scalars().all()
            image_paths = [m.file_path for m in media_list]
            
            # 2. Appeler le service backend pour créer le produit
            product_data = {
                "name": name,
                "price": price,
                "stock": stock,
                "description": description
            }
            
            new_product = await yaburu_service.create_product(store_id, product_data, image_paths)
            
            if not new_product:
                return "Échec de la création du produit sur le serveur Yaburu."
            
            # 3. Vider le tampon d'images après succès
            if media_list:
                await db.execute(delete(PendingMedia).where(PendingMedia.phone == phone))
                await db.commit()
                logger.info(f"🧹 Tampon d'images vidé pour {phone}")
            
            return f"Succès ! Le produit '{name}' a été créé avec {len(image_paths)} image(s)."
            
    except Exception as e:
        logger.error(f"❌ Erreur tool create_store_product: {e}")
        return f"Une erreur technique est survenue : {str(e)}"

@tool(args_schema=FinalAnswer)
def final_answer(answer: str, stats_included: bool = False):
    """
    Appelez cet outil UNIQUEMENT lorsque vous avez terminé votre raisonnement 
    et que vous avez récupéré toutes les informations nécessaires.
    """
    return {"answer": answer, "stats_included": stats_included}

# Dictionnaire centralisé pour l'exécuteur
AVAILABLE_TOOLS = {
    "get_store_stats": get_store_stats,
    "get_store_orders": get_store_orders,
    "get_store_products": get_store_products,
    "create_store_product": create_store_product,
    "get_store_users": get_store_users, 
    "change_store": change_store,
    "final_answer": final_answer 
    }

TOOL_LIST = list(AVAILABLE_TOOLS.values())
