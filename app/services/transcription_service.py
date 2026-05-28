import logging
import os
from typing import Optional
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    async def transcribe_audio(self, file_path: str) -> Optional[str]:
        """Transcrit un fichier audio local (ex: .ogg) en texte brut via OpenAI Whisper"""
        if not self.client:
            logger.error("❌ OpenAI API Key manquante dans la configuration. Impossible de transcrire.")
            return None

        if not os.path.exists(file_path):
            logger.error(f"❌ Fichier audio introuvable : {file_path}")
            return None

        try:
            logger.info(f"🎙️ [WHISPER] Début de la transcription de {file_path}")
            with open(file_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            logger.info(f"✅ [WHISPER] Transcription réussie : '{transcript.text}'")
            return transcript.text
        except Exception as e:
            logger.error(f"❌ [WHISPER] Erreur de transcription : {str(e)}")
            return None

transcription_service = TranscriptionService()
