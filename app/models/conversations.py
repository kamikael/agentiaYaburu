from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func

import uuid

from app.db import Base

class Conversation(Base):
    __tablename__ = "conversation"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("session.id", ondelete="SET NULL"), nullable=True)

    # Colonnes physiques conformes à l'UML
    status = Column(String(50), default="active")
    debut_le = Column(DateTime, server_default=func.now())
    fini_le = Column(DateTime, server_default=func.now())
    dernier_message_le = Column(DateTime, server_default=func.now())
    date_creation = Column(DateTime, server_default=func.now())
    date_mise_a_jour = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Métadonnées additionnelles héritées de la version précédente
    title = Column(String(255))

    # Synonymes pour compatibilité
    started_at = synonym("debut_le")
    ended_at = synonym("fini_le")
    last_message_at = synonym("dernier_message_le")
    created_at = synonym("date_creation")
    updated_at = synonym("date_mise_a_jour")

    # Relations
    session = relationship("Session", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")

    # Propriétés dynamiques pour compatibilité totale avec le code Python existant
    @property
    def user_id(self):
        return self.session.store.utilisateur_id if self.session and self.session.store else None

    @property
    def store_id(self):
        return self.session.boutique_id if self.session else None
        
    @property
    def user(self):
        return self.session.store.user if self.session and self.session.store else None

    @property
    def store(self):
        return self.session.store if self.session else None
