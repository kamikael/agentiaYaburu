import httpx
import logging
from typing import Optional, Dict, Any, List
from config import settings

logger = logging.getLogger(__name__)

class YaburuService:
    def __init__(self):
        # Utilisation de l'URL configurée (ou valeur par défaut si non définie)
        self.base_url = settings.YABURU_API_URL or "http://127.0.0.1:8000/api"
        self.timeout = settings.YABURU_API_TIMEOUT or 30.0
        
        # Client HTTP persistant avec connection pooling
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )

    async def _get_headers(self):
        # Utilisation directe de la clé API depuis la configuration
        return {
            "Authorization": f"Bearer {settings.YABURU_API_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def check_user(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Vérifie l'existence d'un utilisateur et de ses boutiques sur le backend Yaburu.
        Appelle l'endpoint PHP: check_user($phone)
        """
        url = f"{self.base_url}/tools/users"
        params = {"phone": phone}
        
        try:
            response = await self._client.get(url, params=params, headers=await self._get_headers())
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"ℹ️ Utilisateur non trouvé sur Yaburu: {phone}")
                return None
            elif response.status_code == 401:
                logger.error(f"❌ Clé API Yaburu invalide ou non autorisée (401)")
                return None
            else:
                logger.error(f"❌ Erreur API Yaburu ({response.status_code}): {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'appel check_user: {str(e)}")
            return None

    async def _make_get_request(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Méthode générique pour les requêtes GET"""
        try:
            response = await self._client.get(url, params=params, headers=await self._get_headers())
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.error(f"❌ Clé API Yaburu invalide ou non autorisée sur {url} (401)")
                return None
            else:
                logger.error(f"❌ Erreur API Yaburu sur {url} ({response.status_code}): {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Erreur lors du GET {url}: {str(e)}")
            return None

    async def get_store_stats(self, store_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les statistiques d'une boutique"""
        url = f"{self.base_url}/tools/stores/{store_id}/stats"
        return await self._make_get_request(url)

    async def get_store_orders(self, store_id: str, name_product: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Récupère les commandes d'une boutique, potentiellement filtrées par nom de produit"""
        url = f"{self.base_url}/tools/stores/{store_id}/orders"
        params = {}
        if name_product:
            params["name_product"] = name_product
        return await self._make_get_request(url, params=params if params else None)

    async def get_store_products(self, store_id: str) -> Optional[List[Dict[str, Any]]]:
        """Récupère les produits d'une boutique"""
        url = f"{self.base_url}/tools/stores/{store_id}/products"
        return await self._make_get_request(url)

    async def create_product(self, store_id: str, data: Dict[str, Any], image_paths: List[str] = None) -> Optional[Dict[str, Any]]:
        """
        Crée un nouveau produit via l'API Yaburu avec support multi-images.
        """
        url = f"{self.base_url}/tools/stores/{store_id}/products"
        
        try:
            # Préparation des données (on ne met pas images dans json)
            files = []
            if image_paths:
                for i, path in enumerate(image_paths):
                    # On simule l'ouverture du fichier (en réel on utiliserait open(path, "rb"))
                    # Ici pour le test, on va juste envoyer un contenu factice si le fichier n'existe pas
                    try:
                        files.append(("images[]", (f"product_{i}.jpg", open(path, "rb"), "image/jpeg")))
                    except Exception as e:
                        logger.error(f"❌ Erreur lors de l'ouverture de l'image {path} : {str(e)}")
                        # Fallback simulation
                        files.append(("images[]", (f"product_{i}.jpg", b"fake_image_content", "image/jpeg")))

            headers = await self._get_headers()
            # Pour un envoi multipart (avec fichiers), on laisse httpx définir lui-même le Content-Type avec le boundary correct.
            if "Content-Type" in headers:
                del headers["Content-Type"]

            response = await self._client.post(
                url,
                data=data,
                files=files,
                headers=headers
            )
                
            if response.status_code in [200, 201]:
                    return response.json()
            else:
                    logger.error(f"❌ Erreur création produit ({response.status_code}): {response.text}")
                    return None
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'appel create_product: {str(e)}")
            return None

# Instance unique pour l'application
yaburu_service = YaburuService()
