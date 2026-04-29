# main.py
"""Point d'entrée principal - Yaburu ChatBot FastAPI"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import get_settings
from app.api.routes import router as api_router
from app.api.middleware import setup_middleware
from app.utils.errors import CustomException
from app.utils.logging_config import setup_logging

# ================== SETUP ==================

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# ================== LIFESPAN EVENTS ==================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie application"""
    
    # Startup
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔑 Debug mode: {settings.DEBUG}")
    
    # Connexions initiales
    try:
        # Init Supabase
        from app.services.supabase_service import init_supabase
        await init_supabase()
        logger.info("✓ Supabase connected")
        
        # Init Embeddings
        from app.agent.rag import RAGManager
        rag = RAGManager(None)
        logger.info("✓ Embeddings model loaded")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    logger.info("✓ Cleanup completed")

# ================== CREATE APP ==================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Assistant conversationnel IA pour vendeurs Yaburu via WhatsApp",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

# ================== MIDDLEWARE ==================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["graph.instagram.com", "localhost", "127.0.0.1"]
)

# Custom middleware
setup_middleware(app)

# ================== EXCEPTION HANDLERS ==================

@app.exception_handler(CustomException)
async def custom_exception_handler(request, exc):
    """Handle custom exceptions"""
    logger.error(f"CustomException: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request data"}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors"""
    logger.exception(f"Unexpected error: {exc}")
    
    # Send to Sentry if configured
    if settings.SENTRY_DSN:
        import sentry_sdk
        sentry_sdk.capture_exception(exc)
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# ================== ROUTES ==================

# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }

@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness check for K8s"""
    try:
        from app.services.supabase_service import get_supabase
        supabase = get_supabase()
        # Quick test query
        result = supabase.table("users").select("id").limit(1).execute()
        
        return {"ready": True}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"ready": False, "error": str(e)}
        )

# API routes
app.include_router(api_router, prefix="/api")

# ================== STARTUP MESSAGE ==================

@app.on_event("startup")
async def startup_event():
    """Log startup info"""
    logger.info("=" * 60)
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)
    logger.info(f"Host: {settings.HOST}:{settings.PORT}")
    logger.info(f"Workers: {settings.WORKERS}")
    logger.info(f"Debug: {settings.DEBUG}")
    logger.info("=" * 60)

# ================== RUN ==================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS if not settings.DEBUG else 1,
        reload=settings.RELOAD and settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )