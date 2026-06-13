import asyncio
import time
import sys

from app.db import engine

async def test():
    start = time.time()
    try:
        async with engine.connect() as conn:
            print('Connected in', time.time() - start)
    except Exception as e:
        print('Error:', e)
    finally:
        await engine.dispose()

asyncio.run(test())
