import logging
import json
import os
import hashlib
import httpx
from typing import List, Optional, Dict, Any, Union

from app.schemas.webhook import (
    ImageMessage,
    AudioMessage,
    WASenderTextPayload,
    WASenderImagePayload,
    WASenderAudioPayload,
    WASenderDocumentPayload,
)

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Service d'envoi de messages via WASenderAPI.
    Reçoit les objets Pydantic du webhook entrant (ImageMessage, AudioMessage, etc.)
    et construit les payloads sortants appropriés pour WASenderAPI.
    """

    # -------------------------------------------------------------------------
    # MÉTHODES PUBLIQUES D'ENVOI
    # -------------------------------------------------------------------------

    async def send_text_message(self, to: str, body: str) -> bool:
        """Envoie un message texte simple."""
        payload = WASenderTextPayload(to=to, text=body)
        return await self._send(payload.dict(exclude_none=True))

    async def send_image_message(
        self,
        to: str,
        image_url: str,
        caption: Optional[str] = None,
    ) -> bool:
        """Envoie une image avec une légende optionnelle."""
        payload = WASenderImagePayload(to=to, imageUrl=image_url, text=caption)
        return await self._send(payload.dict(exclude_none=True))

    async def send_audio_message(self, to: str, audio_url: str) -> bool:
        """Envoie un fichier audio / note vocale."""
        payload = WASenderAudioPayload(to=to, audioUrl=audio_url)
        return await self._send(payload.dict(exclude_none=True))

    async def send_document_message(
        self,
        to: str,
        document_url: str,
        file_name: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> bool:
        """Envoie un document (PDF, DOCX, etc.)."""
        payload = WASenderDocumentPayload(
            to=to,
            documentUrl=document_url,
            fileName=file_name,
            text=caption,
        )
        return await self._send(payload.dict(exclude_none=True))

    async def send_store_selection(
        self, to: str, stores: List[Dict[str, Any]]
    ) -> bool:
        """Envoie la liste des boutiques sous forme de message texte."""
        store_list_text = (
            "Plusieurs boutiques sont associées à votre compte. "
            "Sur laquelle souhaitez-vous travailler ?\n\n"
            "Répondez avec le *numéro* ou le *nom exact* de la boutique :\n\n"
        )
        for i, store in enumerate(stores, 1):
            store_list_text += f"{i}. *{store['store_name']}*\n"

        return await self.send_text_message(to, store_list_text)

    # -------------------------------------------------------------------------
    # TÉLÉCHARGEMENT DE MÉDIAS ENTRANTS
    # -------------------------------------------------------------------------

    async def download_media(
        self,
        media_url: str,
        file_prefix: str = "media",
        media_key: Optional[str] = None,
    ) -> str:
        """
        Télécharge un média (image ou audio) depuis son URL publique WASenderAPI,
        le décrypte si un media_key est fourni, et le stocke dans le dossier tmp/.

        Args:
            media_url:    URL publique directe du fichier (champ `url` de ImageMessage ou AudioMessage).
            file_prefix:  Préfixe du fichier local ('image' ou 'audio').
            media_key:    Clé de chiffrement du média encodée en Base64 (optionnelle).

        Returns:
            Chemin local du fichier téléchargé.
        """
        os.makedirs("tmp", exist_ok=True)

        # Déduction de l'extension depuis l'URL ou le mimetype
        ext = "jpg"
        if "ogg" in media_url or "audio" in media_url:
            ext = "ogg"
        elif "mp4" in media_url or "video" in media_url:
            ext = "mp4"
        elif "pdf" in media_url:
            ext = "pdf"

        url_hash = hashlib.md5(media_url.encode()).hexdigest()
        file_path = f"tmp/{file_prefix}_{url_hash}.{ext}"

        logger.info(f"📥 [MEDIA] Téléchargement de {media_url} → {file_path}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(media_url)
                if response.status_code == 200:
                    content = response.content
                    
                    # Si une clé média est fournie, on décrypte le contenu
                    if media_key:
                        try:
                            logger.info(f"🔓 [MEDIA] Déchiffrement du média avec la clé fournie...")
                            media_type = "image"
                            if "audio" in file_prefix or "voice" in file_prefix:
                                media_type = "audio"
                            elif "document" in file_prefix:
                                media_type = "document"
                            elif "video" in file_prefix:
                                media_type = "video"
                                
                            content = self._decrypt_media(content, media_key, media_type)
                            logger.info(f"✅ [MEDIA] Déchiffrement réussi !")
                        except Exception as dec_err:
                            logger.error(f"❌ [MEDIA] Échec du déchiffrement : {dec_err}")
                    
                    with open(file_path, "wb") as f:
                        f.write(content)
                    logger.info(f"✅ [MEDIA] Fichier sauvegardé : {file_path}")
                else:
                    logger.error(
                        f"❌ [MEDIA] Erreur {response.status_code} lors du téléchargement de {media_url}"
                    )
        except Exception as e:
            logger.error(f"❌ [MEDIA] Exception pendant le téléchargement : {e}")

        return file_path

    def _decrypt_media(self, content: bytes, media_key_b64: str, media_type: str) -> bytes:
        """Déchiffre les fichiers médias chiffrés par WhatsApp (AES-256-CBC avec HKDF)"""
        import base64
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        # 1. Base64 decode media key
        media_key = base64.b64decode(media_key_b64)
        
        # 2. Get info string based on media type
        info_map = {
            "image": b"WhatsApp Image Keys",
            "audio": b"WhatsApp Audio Keys",
            "video": b"WhatsApp Video Keys",
            "document": b"WhatsApp Document Keys"
        }
        info = info_map.get(media_type, b"WhatsApp Image Keys")
        
        # 3. Derive key stream using HKDF-SHA256
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=112,
            salt=b"\x00" * 32,
            info=info
        )
        key_stream = hkdf.derive(media_key)
        
        iv = key_stream[:16]
        aes_key = key_stream[16:48]
        
        # 4. Strip last 10 bytes (MAC)
        ciphertext = content[:-10]
        
        # 5. Decrypt using AES-CBC
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        # 6. Remove PKCS7 padding
        padding_len = plaintext[-1]
        if 0 < padding_len <= 16:
            if all(x == padding_len for x in plaintext[-padding_len:]):
                plaintext = plaintext[:-padding_len]
                
        return plaintext

    # -------------------------------------------------------------------------
    # MÉTHODE INTERNE D'ENVOI HTTP
    # -------------------------------------------------------------------------

    async def _send(self, data: dict) -> bool:
        """
        Effectue le POST réel vers WASenderAPI.

        Args:
            data: Dictionnaire du payload prêt à envoyer (clés camelCase).
        """
        from config import settings

        url = settings.WHATSAPP_API_URL
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json",
        }

        logger.info(
            f"📤 [OUTBOUND] POST → {url}  payload={json.dumps(data, ensure_ascii=False)}"
        )

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=data, headers=headers)

            if response.status_code in (200, 201):
                logger.info(
                    f"✅ [OUTBOUND] Message envoyé à {data.get('to')} | réponse : {response.text}"
                )
                return True
            else:
                logger.error(
                    f"❌ [OUTBOUND] Échec (HTTP {response.status_code}) : {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ [OUTBOUND] Erreur de connexion : {e}")
            return False


whatsapp_service = WhatsAppService()