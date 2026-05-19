# app/config.py
"""Configuration centralisée du projet Yaburu ChatBot"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv
load_dotenv()
class Settings(BaseSettings):
    """Configuration application"""
    
    # ============ APP ============
    APP_NAME: str = "Yaburu ChatBot IA"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # ============ SERVER ============
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    WORKERS: int = 4
    RELOAD: bool = False
    
    # ============ DB ============
    DATABASE_URL: str = "postgresql+asyncpg://postgres.bfgbhomlnlcebgfczwpu:Kamikael123%40@aws-1-eu-west-3.pooler.supabase.com:6543/postgres"   
    
    # ============ WHATSAPP / META ============
    WHATSAPP_API_URL: str = "https://graph.instagram.com/v18.0"
    WHATSAPP_PHONE_NUMBER_ID: str   = "102373896015622"
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = "421414195902446"
    WHATSAPP_API_TOKEN: str = "EAAVzIZBshP4BOnj0Qz1sFh5g5gI4u6g4uZA74X77Xj7iM139ZAVN5sF0W4gJq071jHlZCZBD8k85K5pZAk5947G4F1l93Q0u7r2b35b4y7v6n31iJ76N5pY6Q97u4c2gQh4bXJ6u71aC577j3ZB4B2p98d7G7wS334Y6u7uB6wY5q65B513O78b1j1v1G5mD503w1349w22g91ZB517W"
    WHATSAPP_SECRET: str    = "b92e306e541c0b33eb1e0a631d3e6fcc"
    WEBHOOK_VERIFY_TOKEN: str = "mon_token_secret_123"
    
    # ============ YABURU API ============
    YABURU_API_URL: str = str(os.getenv("YABURU_API_URL"))
    YABURU_API_KEY: str = str(os.getenv("YABURU_API_KEY"))
    YABURU_API_TIMEOUT: int = 30        
    
    # ============ GOOGLE GEMINI ============
    GEMINI_API_KEY: str = "AIzaSyANcdZUm5OV5dmmQOtkEVVsoaHbLG4rtt8"
    GEMINI_MODEL: str = "google/gemini-2.0-flash-001"
    GEMINI_TEMPERATURE: float = 0.7
    GEMINI_MAX_TOKENS: int = 1024
    AGENT_MAX_HISTORY: int = 10  # Nombre de messages max à conserver dans le contexte
    GEMINI_TIMEOUT: int = 30
    
    # ============ OPENROUTER ============
    OPENROUTER_API_KEY: str = str(os.getenv("OPENROUTER_API_KEY"))
    OPENROUTER_URL: str = str(os.getenv("OPENROUTER_URL"))
    
    # ============ SUPABASE ============
    SUPABASE_URL: str = str(os.getenv("SUPABASE_URL"))
    SUPABASE_KEY: str = str(os.getenv("SUPABASE_KEY"))
    SUPABASE_JWT_SECRET: Optional[str] = None   
    
    # ============ RAG / EMBEDDINGS ============
    EMBEDDINGS_MODEL: str = "distiluse-base-multilingual-cased-v2"
    RAG_TOP_K: int = 3
    RAG_SIMILARITY_THRESHOLD: float = 0.5
    
    # ============ MONITORING & LOGGING ============
    LOG_LEVEL: str = "DEBUG"
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