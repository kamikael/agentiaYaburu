from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import uuid

from app.db import Base

class OutilExecute(Base):
    __tablename__ = "outils_executees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("message.id", ondelete="CASCADE"), nullable=False)

    outil_nom = Column(String(50), nullable=False) # UML has String(20), 50 is safer
    outil_entree = Column(JSONB)
    outil_sortie = Column(JSONB)
    success = Column(Boolean, default=True)
    message_erreur = Column(Text)

    execution_temps = Column(DateTime, server_default=func.now())
    date_creation = Column(DateTime, server_default=func.now())
    date_mise_a_jour = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relations
    message = relationship("Message")
