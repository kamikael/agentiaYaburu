import asyncio
from sqlalchemy import select
from sqlalchemy.orm import configure_mappers
from app.models.user import User
from app.models.conversations import Conversation
from app.models.messages import Message
from app.models.shops import Shop
from app.models.sessions import Session

def test_models():
    try:
        print("Configuring mappers...")
        configure_mappers()
        print("OK: Mappers configured successfully.")
        
        print("Testing select(User)...")
        stmt = select(User)
        print(f"OK: select(User) compiled")
        
        print("Testing select(Conversation)...")
        stmt = select(Conversation)
        print(f"OK: select(Conversation) compiled")
        
        print("Checking relationships...")
        from sqlalchemy.orm import class_mapper
        user_mapper = class_mapper(User)
        print(f"User relationships: {[r.key for r in user_mapper.relationships]}")
        
        conv_mapper = class_mapper(Conversation)
        print(f"Conversation relationships: {[r.key for r in conv_mapper.relationships]}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_models()
