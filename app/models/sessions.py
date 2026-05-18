from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import uuid


from app.db import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="SET NULL"))

    session_token = Column(String(512), unique=True, nullable=False)

    is_active = Column(Boolean, default=True)

    expires_at = Column(DateTime, nullable=False)
    last_activity_at = Column(DateTime, server_default=func.now())

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # relations
    user = relationship("User", back_populates="sessions")
    store = relationship("store", back_populates="sessions")
    conversations = relationship("Conversation", back_populates="session")
