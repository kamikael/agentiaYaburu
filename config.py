# app/config.py
"""Configuration centralisée du projet Yaburu ChatBot"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Configuration application"""
    
    # ============ APP ============
    APP_NAME: str = "Yaburu ChatBot IA"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # ============ SERVER ============
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = False
    
    # ============ WHATSAPP / META ============
    WHATSAPP_API_URL: str = "https://graph.instagram.com/v18.0"
    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_BUSINESS_ACCOUNT_ID: str
    WHATSAPP_API_TOKEN: str
    WHATSAPP_SECRET: str
    WEBHOOK_VERIFY_TOKEN: str
    
    # ============ YABURU API ============
    YABURU_API_URL: str
    YABURU_API_KEY: str
    YABURU_API_TIMEOUT: int = 30
    
    # ============ GOOGLE GEMINI ============
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_TEMPERATURE: float = 0.7
    GEMINI_MAX_TOKENS: int = 1024
    GEMINI_TIMEOUT: int = 30
    
    # ============ SUPABASE ============
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_JWT_SECRET: Optional[str] = None
    
    # ============ RAG / EMBEDDINGS ============
    EMBEDDINGS_MODEL: str = "distiluse-base-multilingual-cased-v2"
    RAG_TOP_K: int = 3
    RAG_SIMILARITY_THRESHOLD: float = 0.5
    
    # ============ MONITORING & LOGGING ============
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: Optional[str] = None
    DATADOG_API_KEY: Optional[str] = None
    DATADOG_APP_KEY: Optional[str] = None
    
    # ============ RATE LIMITING ============
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # en secondes
    
    # ============ CACHE ============
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 3600  # 1 heure
    
    # ============ FEATURE FLAGS ============
    FEATURE_RAG_ENABLED: bool = True
    FEATURE_MULTI_TOOL: bool = True
    FEATURE_ANALYTICS: bool = True
    
    # ============ SECURITY ============
    ALLOWED_ORIGINS: list = [
        "https://www.whatsapp.com",
        "https://graph.instagram.com"
    ]
    SECRET_KEY: str = "your-secret-key-change-in-prod"
    
    class Config:
        """Pydantic config"""
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

@lru_cache()
def get_settings() -> Settings:
    """Retourner settings avec cache"""
    return Settings()

# Accès facile
settings = get_settings()