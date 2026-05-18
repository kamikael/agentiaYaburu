import asyncio
import sys
import os

# Ajout du chemin racine pour l'import des modules app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.webhook_router import webhook_router
from app.db import engine, Base
from config import settings
import logging

# Configuration du logging pour le test
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    print("\n" + "="*50)
    print("🚀 BIENVENUE DANS LE TEST INTERACTIF YABURU (V2)")
    print("="*50)
    print("Nouveau flux : Authentification par numéro uniquement.")
    print("Instructions :")
    print("- Tapez 'reset' pour supprimer l'utilisateur local et recommencer à zéro.")
    print("- Tapez 'exit' pour quitter.")
    print("-" * 50)

    # Demander le numéro de téléphone pour simuler l'identité WhatsApp
    phone = input("\n📱 Entrez un numéro de téléphone (ex: 22967044000) : ").strip()
    if not phone:
        phone = "22967044000"
        print(f"Numéro par défaut utilisé : {phone}")

    async def reset_local_user(phone_num):
        from app.models.user import User
        from app.models.sessions import Session
        from sqlalchemy import delete
        async with AsyncSessionLocal() as db:
            # Récupérer l'ID user
            res = await db.execute(select(User).where(User.phone_number == phone_num))
            u = res.scalar_one_or_none()
            if u:
                # Supprimer sessions et user pour un reset total
                await db.execute(delete(Session).where(Session.user_id == u.id))
                await db.execute(delete(User).where(User.id == u.id))
                await db.commit()
                print(f"🗑️ Utilisateur local {phone_num} et ses sessions supprimés.")
            else:
                print(f"ℹ️ Aucun utilisateur local trouvé pour {phone_num}.")

    while True:
        try:
            # Demander l'input utilisateur
            user_input = input("\n👤 Vous : ").strip()

            if user_input.lower() in ['exit', 'quit', 'quitter', 'stop']:
                print("\n👋 Fin du test. À bientôt !")
                break

            if user_input.lower() == 'reset':
                await reset_local_user(phone)
                print("✨ Prêt pour un nouveau test d'onboarding.")
                continue

            if not user_input:
                continue

            print("⏳ Vérification Yaburu & Routage...")
            
            # route_message s'occupe de tout le nouveau flux
            result = await webhook_router.route_message(phone, text=user_input)
            
            if result != "ROUTED_TO_AGENT":
                # Affiche le résultat si ce n'est pas routé vers l'agent (ex: accès refusé ou onboarding continue)
                print(f"ℹ️ État : {result}")

        except KeyboardInterrupt:
            print("\n👋 Test interrompu.")
            break
        except Exception as e:
            logger.exception("Erreur pendant le test")
            print(f"\n❌ Une erreur est survenue : {e}")

if __name__ == "__main__":
    from sqlalchemy import select
    asyncio.run(main())
