import asyncio
from config import settings
from google import genai
from google.genai import types

async def test_embed():
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    texts = ["hello", "world", "third"]
    res = await client.aio.models.embed_content(
        model="text-embedding-004",
        contents=texts
    )
    print("Without config returned:", len(res.embeddings))

if __name__ == "__main__":
    asyncio.run(test_embed())
