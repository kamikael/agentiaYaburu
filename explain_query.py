import asyncio
from sqlalchemy import text
from app.db import AsyncSessionLocal

async def analyze():
    async with AsyncSessionLocal() as db:
        # EXPLAIN ANALYZE
        query = """
        EXPLAIN ANALYZE 
        SELECT "Session".id 
        FROM "Session" 
        JOIN utilisateur ON "Session".utilisateur_id = utilisateur.id 
        WHERE utilisateur.telephone = '237692818725' 
        AND "Session".est_active = true 
        AND "Session".expire_le > now() 
        ORDER BY "Session".date_creation DESC;
        """
        try:
            res = await db.execute(text(query))
            for row in res:
                print(row[0])
        except Exception as e:
            print("Error executing query:", e)

asyncio.run(analyze())
