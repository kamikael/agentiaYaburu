from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import settings         
        
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"statement_cache_size": 0},
    pool_pre_ping=True,      # Teste la connexion avant chaque utilisation (détecte les connexions coupées)
    pool_recycle=300,        # Recycle les connexions après 5 min (Supabase coupe les idle après ~60s)
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

        