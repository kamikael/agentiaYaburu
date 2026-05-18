import httpx
import asyncio
import json
import uuid

BASE_URL = "http://127.0.0.1:8001"
WHATSAPP_PHONE = "22967044033"

async def send_webhook(payload):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/webhooks/whatsapp",
            json=payload
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response

def create_text_payload(phone, text):
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "106540352242922",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "12345", "phone_number_id": "67890"},
                    "messages": [{
                        "id": f"wamid.{uuid.uuid4().hex}",
                        "from": phone,
                        "timestamp": "1663880309",
                        "type": "text",
                        "text": {"body": text}
                    }]
                }
            }]
        }]
    }

def create_interactive_payload(phone, shop_id):
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "106540352242922",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "12345", "phone_number_id": "67890"},
                    "messages": [{
                        "id": f"wamid.{uuid.uuid4().hex}",
                        "from": phone,
                        "timestamp": "1663880309",
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": {"id": f"shop_{shop_id}", "title": "Boutique Test"}
                        }
                    }]
                }
            }]
        }]
    }

async def simulate_onboarding():
    print("--- 1. Envoi d'un premier message ---")
    await send_webhook(create_text_payload(WHATSAPP_PHONE, "Bonjour !"))
    
    print("\n--- 2. Envoi de l'email ---")
    await send_webhook(create_text_payload(WHATSAPP_PHONE, "dkerenmbarga@gmail.com"))

    print("\n--- 3. Choix de la boutique (Par nom ou ID) ---")
    # On attend un peu que le serveur traite l'étape précédente
    await asyncio.sleep(2)
    # Remplacer 'Ma Boutique' par le nom d'une de vos boutiques réelles pour tester
    await send_webhook(create_text_payload(WHATSAPP_PHONE, "6")) 

if __name__ == "__main__":
    try:
        asyncio.run(simulate_onboarding())
    except Exception as e:
        print(f"Erreur: {e}")
        print("Assurez-vous que l'application FastAPI tourne sur le port 8001 (uv run python main.py)")
