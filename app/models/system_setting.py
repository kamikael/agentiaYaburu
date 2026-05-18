from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from app.db import Base

class SystemSetting(Base):
    """
    Stocke les paramètres de configuration dynamiques (tokens, clés API, etc.)
    """
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text)
    
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, server_default=func.now())
