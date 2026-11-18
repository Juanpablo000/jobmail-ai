from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.database import engine
from app.models import JobOffer  # noqa: F401 — importar para que Base los registre
from app.database import Base
from app.routers import jobs, sync, chat, auth
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación: startup y shutdown."""
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Iniciando JobMail AI...")

    # Intentar inicializar la base de datos (con reintentos o log amigable)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                __import__("sqlalchemy", fromlist=["text"]).text(
                    "CREATE EXTENSION IF NOT EXISTS vector"
                )
            )
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Base de datos conectada y tablas listas")
    except Exception as e:
        logger.warning(
            f"⚠️ No se pudo conectar a PostgreSQL en el arranque: {e}\n"
            "   Asegúrate de iniciar el contenedor de base de datos con: docker-compose up db -d\n"
            f"   (URL configurada: {settings.database_url})"
        )

    # Iniciar scheduler de Gmail
    start_scheduler()

    yield  # ← La app corre aquí

    # ── Shutdown ─────────────────────────────────────────────────────────────
    stop_scheduler()
    await engine.dispose()
    logger.info("JobMail AI detenido")


app = FastAPI(
    title="JobMail AI",
    description="Extrae ofertas laborales de Gmail y permite chatear con ellas via LM Studio",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — permite que el frontend React llame al backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(jobs.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(auth.router)


@app.get("/health", tags=["health"])
async def health():
    """Health check — verificar que el backend está corriendo."""
    return {"status": "ok", "version": "0.1.0"}
