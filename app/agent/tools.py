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
from app.agent.context import store_id_ctx, phone_number_ctx, yaburu_store_id_ctx

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

@tool
async def change_store(new_store_id: str) -> str:
    """ permrt de pivoter vers une autre boutique en utilisant l'id de la boutique."""
    store_id = yaburu_store_id_ctx.get()
    if not store_id:
        return "Erreur : Aucun contexte de boutique trouvé."

    try:
        products = await yaburu_service.get_store_products(new_store_id)
        if not products:
            return "Aucun produit trouvé."
        return json.dumps(products, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in get_store_products tool: {e}")
        return f"Erreur lors de la récupération des produits: {str(e)}"


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
    "final_answer": final_answer 
    }

TOOL_LIST = list(AVAILABLE_TOOLS.values())
