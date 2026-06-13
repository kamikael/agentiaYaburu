# app/config.py
"""Configuration centralisée du projet Yaburu ChatBot"""

import os
from functools import lru_cache
import openai
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
    WHATSAPP_API_URL: str = "https://www.wasenderapi.com/api/send-message"
    WHATSAPP_PHONE_NUMBER_ID: str   = "102373896015622"
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = "421414195902446"
    WHATSAPP_API_TOKEN: str = str(os.getenv("WHATSAPP_API_TOKEN"))
    WHATSAPP_SECRET: str = str(os.getenv("WHATSAPP_SECRET"))
    WEBHOOK_VERIFY_TOKEN: str = str(os.getenv("WEBHOOK_VERIFY_TOKEN"))

    # ============ YABURU API ============
    YABURU_API_URL: str = str(os.getenv("YABURU_API_URL"))
    YABURU_API_KEY: str = str(os.getenv("YABURU_API_KEY"))
    YABURU_API_TIMEOUT: int = 30        
    
    # ============ GOOGLE GEMINI ============
    GEMINI_API_KEY: str = str(os.getenv("GEMINI_API_KEY"))
    GEMINI_MODEL: str = "google/gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.7
    GEMINI_MAX_TOKENS: int = 1024
    AGENT_MAX_HISTORY: int = 6  # Nombre de messages max à conserver dans le contexte (réduit pour accélérer le LLM)
    GEMINI_TIMEOUT: int = 30
    
    # ============ OPENROUTER ============
    OPENROUTER_API_KEY: str = str(os.getenv("OPENROUTER_API_KEY"))
    OPENROUTER_URL: str = str(os.getenv("OPENROUTER_URL"))
    
    # ============ OPENAI ============
    OPENAI_API_KEY: Optional[str] = str(os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
    
    # ============ SUPABASE ============
    SUPABASE_URL: str = str(os.getenv("SUPABASE_URL"))
    SUPABASE_KEY: str = str(os.getenv("SUPABASE_KEY"))
    SUPABASE_JWT_SECRET: Optional[str] = None   
    
    # ============ RAG / EMBEDDINGS ============
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-2" # 768 dimensions
    RAG_CHUNK_SIZE: int = 800
    RAG_CHUNK_OVERLAP: int = 150
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.5
    
    # ============ MONITORING & LOGGING ============
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: Optional[str] = None
    DATADOG_API_KEY: Optional[str] = None
    DATADOG_APP_KEY: Optional[str] = None
    
    # ============ LANGSMITH TRACING ============
    LANGCHAIN_TRACING_V2: str = str(os.getenv("LANGCHAIN_TRACING_V2", "false"))
    LANGCHAIN_ENDPOINT: str = str(os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"))
    LANGCHAIN_API_KEY: Optional[str] = str(os.getenv("LANGCHAIN_API_KEY")) if os.getenv("LANGCHAIN_API_KEY") else None
    LANGCHAIN_PROJECT: str = str(os.getenv("LANGCHAIN_PROJECT", "yaburu_agent"))
    
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

# Assurer que Langchain prend en compte la config LangSmith (même si passée via Docker/env au lieu de .env)
if settings.LANGCHAIN_TRACING_V2.lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
    if settings.LANGCHAIN_API_KEY:
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY