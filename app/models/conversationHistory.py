from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import uuid


from app.db import Base

class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    start_index = Column(Integer, default=0)
    end_index = Column(Integer, default=0)
    window_size = Column(Integer, default=10)

    summary = Column(Text)
    full_context = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())