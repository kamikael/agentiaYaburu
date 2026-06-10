import logging
from typing import List
from google import genai
from google.genai import types
from config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        # Configure Gemini API with new google-genai SDK
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # Utiliser le nouveau modèle gemini-embedding-2 demandé
        self.model_name = "gemini-embedding-2"

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        """
        try:
            result = await self.client.aio.models.embed_content(
                model=self.model_name,
                contents=text,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT", output_dimensionality=768)
            )
            return result.embeddings[0].values
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        """
        try:
            result = await self.client.aio.models.embed_content(
                model=self.model_name,
                contents=query,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY", output_dimensionality=768)
            )
            return result.embeddings[0].values
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of text strings.
        """
        if not texts:
            return []
            
        try:
            import asyncio
            results = []
            
            # Traitement strictement séquentiel pour respecter le quota Free Tier (100 requêtes/minute)
            for i, text in enumerate(texts):
                success = False
                retries = 0
                while not success and retries < 3:
                    try:
                        # Délai de base pour lisser les requêtes (~1.5s par requête = 40 req/min)
                        await asyncio.sleep(1.5)
                        
                        res = await self.client.aio.models.embed_content(
                            model=self.model_name,
                            contents=text,
                            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT", output_dimensionality=768)
                        )
                        results.append(res.embeddings[0].values)
                        success = True
                    except Exception as e:
                        error_str = str(e)
                        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                            retries += 1
                            logger.warning(f"Rate limit hit (429). Waiting 60 seconds before retry {retries}/3...")
                            await asyncio.sleep(60) # Attendre 1 minute complète de reset de quota
                        else:
                            raise e
                            
            return results
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise

embedding_service = EmbeddingService()
