import asyncio
from sqlalchemy import select
from app.db import AsyncSessionLocal
from app.models.pendingMedia import PendingMedia

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(PendingMedia))
        media = res.scalars().all()
        print(f"Total pending media: {len(media)}")
        for m in media:
            print(f"- ID: {m.id}, Phone: {m.phone}, File Path: {m.file_path}, Media Type: {m.media_type}, Media ID: {m.media_id}, Created At: {m.created_at}")

if __name__ == "__main__":
    asyncio.run(main())
