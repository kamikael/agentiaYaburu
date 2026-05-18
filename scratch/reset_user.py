import asyncio
from app.db import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import update

async def reset():
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(User)
            .where(User.phone_number == '22967044000')
            .values(onboarding_step='waiting_for_shop')
        )
        await db.commit()
        print("User 22967044000 reset to waiting_for_shop")

if __name__ == "__main__":
    asyncio.run(reset())
