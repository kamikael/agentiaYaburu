import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from app.db import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.models.stores import Shop
from app.models.sessions import Session
from app.models.conversations import Conversation
from app.services.webhook_router import webhook_router

async def setup_test_data():
    """Prépare les données en base pour le test de l'agent"""
    phone = "22967044000"
    email = "kamikaelmbarga@gmail.com"
    
    async with AsyncSessionLocal() as db:
        # 1. Rechercher ou créer l'utilisateur
        result = await db.execute(select(User).where(User.phone_number == phone))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                phone_number=phone,
                email=email,
                first_name="Kamikael",
                onboarding_step="completed"
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"✅ Utilisateur créé: {user.id}")
        else:
            user.onboarding_step = "completed"
            await db.commit()
            print(f"✅ Utilisateur existant: {user.id}")

        # 2. Rechercher ou créer la boutique
        shop_result = await db.execute(select(Shop).where(Shop.user_id == user.id))
        shop = shop_result.scalar_one_or_none()
        
        if not shop:
            shop = Shop(
                user_id=user.id,
                yaburu_shop_id="1", # ID de test sur votre backend
                shop_name="Ma Boutique Test",
                shop_url="http://test.shop"
            )
            db.add(shop)
            await db.commit()
            await db.refresh(shop)
            print(f"✅ Boutique créée: {shop.id}")
        else:
            print(f"✅ Boutique existante: {shop.id}")

        # 3. Créer une session active
        session_result = await db.execute(
            select(Session).where(
                and_(Session.user_id == user.id, Session.is_active == True)
            )
        )
        session = session_result.scalar_one_or_none()
        
        if not session:
            session = Session(
                user_id=user.id,
                shop_id=shop.id,
                session_token="test_token_" + str(uuid.uuid4())[:8],
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
            print(f"✅ Session créée: {session.id}")
        else:
            print(f"✅ Session existante: {session.id}")
            
    return phone, user, shop

async def run_test():
    print("--- 🚀 Lancement du test de l'Agent IA ---")
    
    # Préparer les données
    phone, user, shop = await setup_test_data()
    
    # Message de test
    test_message = "Quelles sont les statistiques de ma boutique ?"
    print(f"\n📩 Message envoyé : '{test_message}'")
    
    # Simuler l'arrivée du message sur le routeur
    response = await webhook_router.route_message(phone, text=test_message)
    print(f"\n🚦 Résultat du routage : {response}")
    
    print("\n--- ✅ Test terminé ---")

if __name__ == "__main__":
    # Note: Assurez-vous que les tables existent (alembic upgrade head)
    asyncio.run(run_test())
