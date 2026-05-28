from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func

import uuid

from app.db import Base

class store(Base):
    __tablename__ = "boutique"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    utilisateur_id = Column(UUID(as_uuid=True), ForeignKey("utilisateur.id", ondelete="CASCADE"), nullable=False)

    # Colonnes physiques conformes à l'UML
    yaburu_boutique_id = Column(String(255), nullable=False, unique=True)
    active = Column(Boolean, default=True)
    boutique_nom = Column(String(255))
    boutique_description = Column(Text)
    boutique_url = Column(String(500))
    date_creation = Column(DateTime, server_default=func.now())
    date_mise_a_jour = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Métadonnées additionnelles héritées de la version précédente
    yaburu_access_token = Column(Text, nullable=True) 
    token_expires_at = Column(DateTime)
    is_primary = Column(Boolean, default=False)
    last_sync_at = Column(DateTime)
    sync_status = Column(String(50), default="active") 

    # Synonymes pour compatibilité totale avec le code existant
    user_id = synonym("utilisateur_id")
    yaburu_store_id = synonym("yaburu_boutique_id")
    is_active = synonym("active")
    store_name = synonym("boutique_nom")
    store_description = synonym("boutique_description")
    store_url = synonym("boutique_url")
    created_at = synonym("date_creation")
    updated_at = synonym("date_mise_a_jour")

    # Relations
    user = relationship("User", back_populates="stores")
    conversations = relationship("Conversation", secondary="session", viewonly=True)
    sessions = relationship("Session", back_populates="store")
    products = relationship("Product", back_populates="store")
