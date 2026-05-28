import asyncio
import logging
from sqlalchemy import select, delete
from app.db import AsyncSessionLocal
from app.models.user import User
from app.models.messageQueue import MessageQueue
from app.services.webhook_router import webhook_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def simulate_concurrent_webhooks():
    phone = "22957489231"
    
    # 1. Nettoyer la file d'attente existante et s'assurer que le verrou de l'utilisateur est déverrouillé
    async with AsyncSessionLocal() as db:
        await db.execute(delete(MessageQueue).where(MessageQueue.phone == phone))
        user_res = await db.execute(select(User).where(User.telephone == phone))
        user = user_res.scalar_one_or_none()
        if user:
            user.traitement_en_cours = False
            await db.commit()
            print(f"[INIT] Base de données initialisée et verrou libéré pour {phone}")
        else:
            print(f"[WARN] Utilisateur {phone} non trouvé dans la base locale")
            return
            
    # 2. Simuler l'envoi simultané de 3 messages espacés de 200ms
    print("\n[START] Lancement des appels concurrents au webhook...")
    
    async def call_router(text, delay):
        await asyncio.sleep(delay)
        print(f"[WEBHOOK] Webhook reçu : '{text}' (délai : {delay}s)")
        res = await webhook_router.route_message(phone=phone, text=text)
        print(f"[ROUTE_RES] Statut de routage pour '{text}' : {res}")

    # Envoi de "Bonjour", "Je voudrais ajouter un produit", et "C'est de type physique"
    tasks = [
        call_router("Bonjour", 0.0),
        call_router("Je voudrais ajouter un produit", 0.3),
        call_router("C'est de type physique", 0.6)
    ]
    
    await asyncio.gather(*tasks)
 
    # 3. Attendre la fin du debounce (2,5s) + traitement simulé
    print("\n[WAIT] Attente de la coalescence et du traitement...")
    await asyncio.sleep(6.0)
    
    # 4. Vérifier si tout a bien été vidé et si le verrou est libéré
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(MessageQueue).where(MessageQueue.phone == phone))
        queued = res.scalars().all()
        print(f"\n[RESULTS] Résultat final :")
        print(f"- Messages restants en file d'attente : {len(queued)}")
        
        user_res = await db.execute(select(User).where(User.telephone == phone))
        user = user_res.scalar_one_or_none()
        print(f"- Verrou de traitement_en_cours : {user.traitement_en_cours if user else 'N/A'}")

if __name__ == "__main__":
    asyncio.run(simulate_concurrent_webhooks())
