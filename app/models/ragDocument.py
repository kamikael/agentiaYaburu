from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid


from app.db import Base

class RagDocument(Base):
    
    __tablename__ = "rag_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    document_type = Column(String(50))
    category = Column(String(100))
    tags = Column(ARRAY(Text))

    source_url = Column(Text)

    embedding = Column(Vector(384))

    retrieval_count = Column(Integer, default=0)
    last_retrieved_at = Column(DateTime)

    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime)