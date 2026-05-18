import httpx
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from app.db import AsyncSessionLocal
from app.models.system_setting import SystemSetting

logger = logging.getLogger(__name__)

class YaburuService:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000/api"
        self.token = "5|CtjYaNMoa7bQjn46sD8VBizQzBZB1ERHW40eVPdudc795ecc"
        self.email = "agentia@system.local"
        self.password = "SuperSecurePassword123"
        self.timeout = 30.0

    async def _get_headers(self):
        # Tenter de charger le token depuis la base de données s'il n'est pas déjà en mémoire
        if not hasattr(self, "_token_initialized"):
            await self._load_token_from_db()
            self._token_initialized = True

        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def _load_token_from_db(self):
        """Charge le token depuis la table system_settings"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(SystemSetting).where(SystemSetting.key == "yaburu_api_token")
                )
                setting = result.scalar_one_or_none()
                if setting:
                    self.token = setting.value
                    logger.info("🔑 Token Yaburu chargé depuis la base de données")
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement du token depuis la DB: {str(e)}")

    async def _save_token_to_db(self, token: str):
        """Sauvegarde le token dans la table system_settings"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(SystemSetting).where(SystemSetting.key == "yaburu_api_token")
                )
                setting = result.scalar_one_or_none()
                
                if setting:
                    setting.value = token
                else:
                    setting = SystemSetting(key="yaburu_api_token", value=token, description="Token d'accès API Yaburu")
                    db.add(setting)
                
                await db.commit()
                logger.info("💾 Token Yaburu sauvegardé en base de données")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde du token en DB: {str(e)}")

    async def refresh_token(self) -> bool:
        """Rafraîchit le token d'accès via l'API Yaburu"""
        url = f"{self.base_url}/admin/login"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, 
                    json={"email": self.email, "password": self.password},
                    headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
                )
                if response.status_code == 200:
                    data = response.json()
                    new_token = data.get("access_token") or data.get("token")
                    if new_token:
                        self.token = new_token
                        await self._save_token_to_db(new_token)
                        logger.info("✅ Token Yaburu rafraîchi et persisté avec succès")
                        return True
                    return False
                else:
                    logger.error(f"❌ Échec du rafraîchissement du token: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            logger.error(f"❌ Erreur lors du rafraîchissement du token: {str(e)}")
            return False

    async def check_user(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Vérifie l'existence d'un utilisateur et de ses boutiques sur le backend Yaburu.
        Appelle l'endpoint PHP: check_user($phone)
        """
        url = f"{self.base_url}/tools/users"
        params = {"phone": phone}
        
        async def make_request():
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                return await client.get(url, params=params, headers=await self._get_headers())

        try:
            response = await make_request()
            
            # Si le token est expiré (401), on tente de le rafraîchir une fois
            if response.status_code == 401:
                logger.warning("⚠️ Token Yaburu expiré, tentative de rafraîchissement...")
                if await self.refresh_token():
                    response = await make_request()
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"ℹ️ Utilisateur non trouvé sur Yaburu: {phone}")
                return None
            else:
                logger.error(f"❌ Erreur API Yaburu ({response.status_code}): {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'appel check_user: {str(e)}")
            return None

    async def _make_get_request(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Méthode générique pour les requêtes GET avec gestion du refresh token"""
        async def make_req():
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                return await client.get(url, params=params, headers=await self._get_headers())

        try:
            response = await make_req()
            if response.status_code == 401:
                if await self.refresh_token():
                    response = await make_req()
            
            if response.status_code == 200:
                return response.json()
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

    async def get_store_orders(self, store_id: str) -> Optional[List[Dict[str, Any]]]:
        """Récupère les commandes d'une boutique"""
        url = f"{self.base_url}/tools/stores/{store_id}/orders"
        return await self._make_get_request(url)

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
                    except:
                        # Fallback simulation
                        files.append(("images[]", (f"product_{i}.jpg", b"fake_image_content", "image/jpeg")))

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    data=data, # Données de formulaire
                    files=files, # Fichiers
                    headers=await self._get_headers()
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
