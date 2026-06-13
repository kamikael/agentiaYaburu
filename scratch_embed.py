import asyncio
from config import settings
from google import genai
import inspect

async def check():
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    print("models:")
    print(dir(client.aio.models))
    print("batches:")
    print(dir(client.aio.batches))

if __name__ == "__main__":
    asyncio.run(check())
