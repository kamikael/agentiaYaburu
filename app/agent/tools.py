import json
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from app.services.yaburu_service import yaburu_service # On importe l'instance directement
from app.agent.context import store_id_ctx

from sqlalchemy import select, and_
from app.db import AsyncSessionLocal
from app.models.products import Product
from app.models.user import User
from app.models.stores import store as StoreModel
from app.agent.context import phone_number_ctx
from typing import List
from datetime import datetime, timedelta
import secrets

logger = logging.getLogger(__name__)

class FinalAnswer(BaseModel):
    """Réponse finale structurée à envoyer à l'utilisateur."""
    answer: str = Field(description="La réponse textuelle claire et concise pour le marchand.")
    stats_included: bool = Field(default=False, description="Indique si des statistiques ont été incluses dans la réponse.")

class StoreActionSchema(BaseModel):
    yaburu_boutique_id: str = Field(..., description="L'ID Yaburu de la boutique.")

@tool(args_schema=StoreActionSchema)
async def get_store_stats(yaburu_boutique_id: str) -> str:
    """Récupère les statistiques complètes de la boutique (produits, ventes, clients, revenus)."""
    try:
        stats = await yaburu_service.get_store_stats(yaburu_boutique_id)
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

class GetOrdersSchema(BaseModel):
    yaburu_boutique_id: str = Field(..., description="L'ID Yaburu de la boutique.")
    name_product: Optional[str] = Field(None, description="Nom du produit pour filtrer les commandes actuelles.")

@tool(args_schema=GetOrdersSchema)
async def get_store_orders(yaburu_boutique_id: str, name_product: Optional[str] = None) -> str:
    """Récupère la liste des commandes passées dans la boutique, avec la possibilité de filtrer par produit."""
    try:
        orders = await yaburu_service.get_store_orders(yaburu_boutique_id, name_product)
        if not orders:
            return "Aucune commande trouvée." if not name_product else f"Aucune commande trouvée pour le produit '{name_product}'."
        return json.dumps(orders, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in get_store_orders tool: {e}")
        return f"Erreur lors de la récupération des commandes: {str(e)}"

@tool(args_schema=StoreActionSchema)
async def get_store_products(yaburu_boutique_id: str) -> str:
    """Récupère la liste complète de tous les produits disponibles dans la boutique.
    Sert à vérifier les stocks, prix, et descriptions.
    """
    try:
        products = await yaburu_service.get_store_products(yaburu_boutique_id)
        if not products:
            return "Aucun produit trouvé."
        return json.dumps(products, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in get_store_products tool: {e}")
        return f"Erreur lors de la récupération des produits: {str(e)}"


class CreateProductSchema(BaseModel):
    yaburu_boutique_id: str = Field(..., description="L'ID Yaburu de la boutique.")
    name: str = Field(..., description="Le nom du nouveau produit.")
    price: float = Field(..., description="Le prix de vente du produit.")
    stock: int = Field(..., description="La quantité initiale en stock.")
    product_type: str = Field(..., description="Le type du produit. Doit etre obligatoirement 'physique' ou 'service'.")
    description: str = Field(..., description="La description du produit.")
    purchase_instructions: str = Field(..., description="Les instructions d'achat (ex: 'Contactez-moi sur WhatsApp').")
    image_paths: List[str] = Field(default=[], description="Liste des chemins locaux absolus des images (extraits depuis le texte).")

@tool(args_schema=CreateProductSchema)
async def create_store_product(yaburu_boutique_id: str, name: str, price: float, stock: int, product_type: str, purchase_instructions: str, description: str, image_paths: List[str] = None) -> str:
    """
    Crée un nouveau produit dans la boutique. 
    L'envoi d'au moins une image (son chemin) est strictement obligatoire.
    """
    if not image_paths:
        image_paths = []
        
    phone = phone_number_ctx.get()
    
    if not yaburu_boutique_id or not phone:
        return "Erreur : Contexte manquant (yaburu_boutique_id ou phone)."

    try:
        async with AsyncSessionLocal() as db:
            # Une image au moins est obligatoire pour valider la création
            if not image_paths:
                return "Erreur : Impossible de créer le produit. Aucune image fournie. Demandez au marchand d'envoyer l'image d'abord."
            
            # Normalisation et validation du type de produit
            normalized_type = (product_type or "physique").strip().lower()
            if normalized_type not in ("physique", "service"):
                return f"Erreur : Le type de produit '{product_type}' n'est pas valide."

            # Appeler le service backend pour créer le produit
            product_data = {
                "name": name,
                "price": price,
                "quantity": stock,
                "product_type": normalized_type,
                "purchase_instructions": purchase_instructions,
                "description": description
            }
            
            new_product = await yaburu_service.create_product(yaburu_boutique_id, product_data, image_paths)
            
            if not new_product:
                return "Échec de la création du produit sur le serveur Yaburu."
            
            # Stocker le produit en base de données locale
            store_res = await db.execute(select(StoreModel).where(StoreModel.yaburu_store_id == yaburu_boutique_id))
            store_obj = store_res.scalar_one_or_none()
            if store_obj:
                local_product = Product(
                    boutique_id=store_obj.id,
                    type_produit=normalized_type,
                    nom=name,
                    description=description,
                    prix=price,
                    quantite=stock,
                    chemin_fichier=image_paths[0] if image_paths else None,
                    status="publié",
                    instruction_achat=purchase_instructions,
                    yaburu_produit_id=str(new_product.get("id")) if isinstance(new_product, dict) else None
                )
                db.add(local_product)
                await db.flush() # Pour obtenir local_product.id
                
                # Ajout de toutes les images en tant qu'AttachmentFile
                if image_paths:
                    from app.models.attachment_file import AttachmentFile
                    for path in image_paths:
                        attachment = AttachmentFile(
                            product_id=local_product.id,
                            file_path=path,
                            file_type="image/jpeg" # Type par défaut, peut être ajusté selon l'extension si nécessaire
                        )
                        db.add(attachment)
                        
                await db.commit()
                logger.info(f"💾 Produit '{name}' enregistré localement pour la boutique {store_obj.id} avec {len(image_paths)} image(s)")
            
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

class SearchKnowledgeBaseSchema(BaseModel):
    query: str = Field(..., description="La question ou le sujet à rechercher dans la base de connaissances.")

@tool(args_schema=SearchKnowledgeBaseSchema)
async def search_knowledge_base(query: str) -> str:
    """
    Recherche des informations dans la base de connaissances Yaburu (règles, guides, procédures, etc.).
    Utilise cet outil quand le marchand pose une question générale sur le fonctionnement de Yaburu ou demande de l'aide.
    """
    try:
        from app.services.rag_service import rag_service
        results = await rag_service.search(query=query)
        if not results:
            return "Aucune information trouvée dans la base de connaissances pour cette requête."
        
        # Formater les résultats
        formatted_results = []
        for i, r in enumerate(results, 1):
            source = r.get("metadata", {}).get("title", "Document")
            content = r.get("content", "").strip()
            formatted_results.append(f"Source {i} ({source}):\n{content}")
            
        return "\n\n---\n\n".join(formatted_results)
    except Exception as e:
        logger.error(f"❌ Erreur tool search_knowledge_base: {e}")
        return f"Une erreur est survenue lors de la recherche : {str(e)}"

AVAILABLE_TOOLS = {
    "get_store_stats": get_store_stats,
    "get_store_orders": get_store_orders,
    "get_store_products": get_store_products,
    "create_store_product": create_store_product,
    "get_store_users": get_store_users, 
    "search_knowledge_base": search_knowledge_base,
    "final_answer": final_answer 
    }

TOOL_LIST = list(AVAILABLE_TOOLS.values())
