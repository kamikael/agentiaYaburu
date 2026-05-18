from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import uuid


from app.db import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Contenu
    role = Column(String(20), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)

    # Type et format
    message_type = Column(String(50), default="text")
    format = Column(String(20), default="plain")


    # WhatsApp
    whatsapp_message_id = Column(String(255), unique=True)
    whatsapp_status = Column(String(50))

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relations
    user = relationship("User", back_populates="messages")
    conversation = relationship("Conversation", back_populates="messages")
