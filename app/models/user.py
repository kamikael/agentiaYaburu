from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import uuid


from app.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    phone_number = Column(String(20), unique=True, nullable=False)
    email = Column(String(255), unique=True)

    # Profil
    first_name = Column(String(100))
    last_name = Column(String(100))

    # Métadonnées
    language_preference = Column(String(10), default="fr")
    timezone = Column(String(50), default="Africa/Porto-Novo")

    last_seen_at = Column(DateTime)

    # Onboarding
    onboarding_step = Column(String(50), default="waiting_for_store")
    temp_email = Column(String(255))

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime)

    # Relations
    conversations = relationship("Conversation", back_populates="user")
    stores = relationship("store", back_populates="user")
    messages = relationship("Message", back_populates="user")
    sessions = relationship("Session", back_populates="user")

