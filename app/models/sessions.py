from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func

import uuid

from app.db import Base

class Session(Base):
    __tablename__ = "session"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    utilisateur_id = Column(UUID(as_uuid=True), ForeignKey("utilisateur.id", ondelete="CASCADE"), nullable=False)

    # Colonnes physiques conformes à l'UML
    session_token = Column(String(512), unique=True, nullable=False)
    est_active = Column(Boolean, default=True)
    expire_le = Column(DateTime, nullable=False)
    date_creation = Column(DateTime, server_default=func.now())
    date_mise_a_jour = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Métadonnées additionnelles héritées de la version précédente
    last_activity_at = Column(DateTime, server_default=func.now())

    # Synonymes pour compatibilité
    user_id = synonym("utilisateur_id")
    is_active = synonym("est_active")
    expires_at = synonym("expire_le")
    created_at = synonym("date_creation")
    updated_at = synonym("date_mise_a_jour")

    # relations
    user = relationship("User", back_populates="sessions")
    conversations = relationship("Conversation", back_populates="session")
