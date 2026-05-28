from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func

import uuid

from app.db import Base

class ConversationHistory(Base):
    __tablename__ = "memoire_conversationnelle"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversation.id", ondelete="CASCADE"), nullable=False)

    # Colonnes physiques conformes à l'UML
    debut_index = Column(Integer, default=0)
    fin_index = Column(Integer, default=0)
    taille_fenetre_context = Column(Integer, default=10)
    resumeText = Column(Text)
    context = Column(Text)
    date_creation = Column(DateTime, server_default=func.now())
    date_mise_a_jour = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Synonymes pour compatibilité
    start_index = synonym("debut_index")
    end_index = synonym("fin_index")
    window_size = synonym("taille_fenetre_context")
    summary = synonym("resumeText")
    full_context = synonym("context")
    created_at = synonym("date_creation")
    updated_at = synonym("date_mise_a_jour")

    # Relations
    conversation = relationship("Conversation")

    # Propriété dynamique pour compatibilité totale avec le code Python existant
    @property
    def user_id(self):
        return self.conversation.user_id if self.conversation else None

    @property
    def user(self):
        return self.conversation.user if self.conversation else None