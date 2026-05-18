from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import uuid


from app.db import Base

class store(Base):
    __tablename__ = "stores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    yaburu_store_id = Column(String(255), nullable=False, unique=True)
    yaburu_access_token = Column(Text, nullable=True) 
    token_expires_at = Column(DateTime)
    
    store_name = Column(String(255))
    store_description = Column(Text)
    store_url = Column(String(500))
    
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    
    last_sync_at = Column(DateTime)
    sync_status = Column(String(50), default="active") 
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

     # Relations
    user = relationship("User", back_populates="stores")
    conversations = relationship("Conversation", back_populates="store")
    sessions = relationship("Session", back_populates="store")



