from sqlalchemy import Column, String, DateTime, Text
from datetime import datetime
from app.db import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID

class MessageQueue(Base):
    """
    Modèle pour la file d'attente temporaire des messages d'un utilisateur.
    Permet de regrouper les messages rapides envoyés successivement (coalescence)
    et de mettre en attente les nouveaux messages pendant que l'agent IA répond.
    """
    __tablename__ = "file_d_attente_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), nullable=False, index=True)
    text = Column(Text, nullable=True)
    audio_data = Column(Text, nullable=True) # JSON ou chaîne de texte pour les métadonnées audio
    image_data = Column(Text, nullable=True) # JSON ou chaîne de texte pour les métadonnées image
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MessageQueue(id={self.id}, phone={self.phone}, has_text={bool(self.text)}, created_at={self.created_at})>"
