from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID

class PendingMedia(Base):
    """
    Stocke temporairement les médias (images) envoyés par l'utilisateur
    avant qu'ils ne soient rattachés à une action (ex: création de produit).
    """
    __tablename__ = "pending_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String, nullable=False, index=True)
    media_id = Column(String, nullable=True) # ID WhatsApp du média
    file_path = Column(String, nullable=False) # Chemin local ou URL temporaire
    media_type = Column(String, default="image")
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PendingMedia(phone={self.phone}, type={self.media_type}, path={self.file_path})>"
