from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

import uuid

from app.db import Base

class RechercheContextuelle(Base):
    __tablename__ = "recherche_contextuelle"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("message.id", ondelete="CASCADE"), nullable=False)

    requete = Column(Text, nullable=False)
    requete_embedding = Column(Vector(384))
    documents_trouve = Column(JSONB)
    seuil_de_similarite = Column(Numeric(3, 2), default=0.70)
    documents_utilises = Column(JSONB)

    date_creation = Column(DateTime, server_default=func.now())
    date_mise_a_jour = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Synonymes pour compatibilité totale avec RagRetrieval
    query = synonym("requete")
    query_embedding = synonym("requete_embedding")
    documents_retrieved = synonym("documents_trouve")
    similarity_threshold = synonym("seuil_de_similarite")
    documents_used = synonym("documents_utilises")
    created_at = synonym("date_creation")
    updated_at = synonym("date_mise_a_jour")

    # Relations
    message = relationship("Message")
