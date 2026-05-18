from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import uuid


from app.db import Base

class AdminLog(Base):
    __tablename__ = "admin_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    admin_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

    action_type = Column(String(100), nullable=False)
    target_type = Column(String(50))
    target_id = Column(UUID(as_uuid=True))

    description = Column(Text)
    meta_data = Column("metadata", JSONB)

    ip_address = Column(String(45))
    user_agent = Column(Text)

    created_at = Column(DateTime, server_default=func.now())