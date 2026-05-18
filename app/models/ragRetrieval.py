from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid


from app.db import Base

class RagRetrieval(Base):
    __tablename__ = "rag_retrievals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"))
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"))

    query = Column(Text, nullable=False)
    query_embedding = Column(Vector(384))

    documents_retrieved = Column(JSONB)

    top_k = Column(Integer, default=3)
    similarity_threshold = Column(Numeric(3, 2), default=0.70)

    retrieval_method = Column(String(50), default="vector")

    duration_ms = Column(Integer)

    was_helpful = Column(Boolean)
    feedback = Column(Text)
    documents_used = Column(JSONB)

    created_at = Column(DateTime, server_default=func.now())