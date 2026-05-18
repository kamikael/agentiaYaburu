from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import uuid


from app.db import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)

    title= Column(String(255))
    status = Column(String(50), default="active")
    
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, server_default=func.now())
    last_message_at = Column(DateTime, server_default=func.now())

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="conversations")
    store = relationship("store", back_populates='conversations')
    session = relationship("Session", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
