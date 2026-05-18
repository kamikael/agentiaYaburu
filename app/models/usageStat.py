from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import uuid


from app.db import Base


class UsageStat(Base):
    __tablename__ = "usage_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="SET NULL"))

    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    total_conversations = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)

    total_tokens_used = Column(Integer, default=0)
    total_cost_usd = Column(Numeric(10, 4), default=0)

    queries_support = Column(Integer, default=0)
    queries_product_creation = Column(Integer, default=0)
    queries_sales = Column(Integer, default=0)
    queries_stock = Column(Integer, default=0)
    queries_analytics = Column(Integer, default=0)

    avg_rating = Column(Numeric(3, 2))
    total_ratings = Column(Integer, default=0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "period_start", "period_end", name="uq_usage_period"),
    )