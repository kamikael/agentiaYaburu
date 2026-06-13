from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db import Base

class AttachmentFile(Base):
    __tablename__ = "attachment_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("produits.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_type = Column(String(50), default="image/jpeg")
    
    date_creation = Column(DateTime, server_default=func.now())

    product = relationship("Product", back_populates="attachments")
