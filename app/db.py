from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import settings         
import socket
from urllib.parse import urlparse, urlunparse

# --- Hack Anti-IPv6 (Résolution des 20 secondes d'attente) ---
# Supabase fournit des adresses IPv6 et IPv4, mais asyncpg essaie IPv6 en premier.
# Si le réseau local ne supporte pas l'IPv6, asyncpg attend le timeout OS (20s) avant de passer à l'IPv4.
# On force ici la résolution DNS en IPv4 pur.
db_url = settings.DATABASE_URL
try:
    parsed = urlparse(db_url)
    if parsed.hostname:
        ipv4 = socket.gethostbyname(parsed.hostname)
        db_url = db_url.replace(parsed.hostname, ipv4)
except Exception as e:
    pass # Fallback à l'URL originale en cas d'erreur de parsing

engine = create_async_engine(
    db_url,
    echo=settings.DEBUG,
    connect_args={
        "statement_cache_size": 0
    },
    pool_pre_ping=True,      # Teste la connexion avant chaque utilisation (détecte les connexions coupées)
    pool_recycle=300,        # On remet à 5min car les reconnexions seront maintenant instantanées (plus de délai IPv6)
    pool_size=10,            # Nombre de connexions persistantes
    max_overflow=20,         # Connexions supplémentaires en pic de charge
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

        