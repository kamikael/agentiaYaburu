from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func

import uuid

from app.db import Base

class Message(Base):
    __tablename__ = "message"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversation.id", ondelete="CASCADE"), nullable=False)

    # Colonnes physiques conformes à l'UML
    role = Column(String(20), nullable=False)  # agent, humain, system, tool
    boutique_ciblee_id = Column(UUID(as_uuid=True), ForeignKey("boutique.id", ondelete="SET NULL"), nullable=True)
    contenu = Column(Text, nullable=False)
    date_creation = Column(DateTime, server_default=func.now())
    date_mise_a_jour = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Métadonnées additionnelles héritées de la version précédente
    type_message = Column(String(50), default="texte") # texte, image, document
    format = Column(String(20), default="plain")
    wa_message_id = Column(String(255), unique=True)
    whatsapp_status = Column(String(50))
    tokens_utilises = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)

    # Synonymes pour compatibilité
    content = synonym("contenu")
    message_type = synonym("type_message")
    whatsapp_message_id = synonym("wa_message_id")
    created_at = synonym("date_creation")
    updated_at = synonym("date_mise_a_jour")

    # Relations
    conversation = relationship("Conversation", back_populates="messages")

    # Propriété dynamique pour compatibilité totale avec le code Python existant
    @property
    def user_id(self):
        return self.conversation.user_id if self.conversation else None

    @property
    def user(self):
        return self.conversation.user if self.conversation else None
