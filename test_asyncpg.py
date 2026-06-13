import asyncio
import time
import asyncpg

async def test():
    start = time.time()
    try:
        conn = await asyncpg.connect('postgresql://postgres.bfgbhomlnlcebgfczwpu:Kamikael123%40@13.36.13.135:6543/postgres')
        print('Connected in', time.time() - start)
        await conn.close()
    except Exception as e:
        print('Error:', e)

asyncio.run(test())
