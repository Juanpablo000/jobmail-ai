from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Motor asíncrono de PostgreSQL
engine = create_async_engine(
    settings.database_url,
    echo=False,          # True para ver SQL en consola (útil en desarrollo)
    pool_size=10,
    max_overflow=20,
)

# Fábrica de sesiones asíncronas
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Clase base de la que heredan todos los modelos SQLAlchemy."""
    pass


async def get_db():
    """Dependency de FastAPI que provee una sesión de BD por request."""
    async with AsyncSessionLocal() as session:
        yield session
