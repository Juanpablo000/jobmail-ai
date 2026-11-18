"""
Scheduler APScheduler — sincronización automática de Gmail.
Se inicializa en el lifespan de FastAPI (app/main.py).
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _sync_job():
    """
    Job que corre cada N minutos para sincronizar emails de Gmail.
    Obtiene su propia sesión de BD.
    """
    from app.database import AsyncSessionLocal
    from app.services.sync_service import SyncService

    logger.info("Scheduler: iniciando sincronización automática de Gmail...")
    try:
        async with AsyncSessionLocal() as db:
            service = SyncService()
            stats = await service.sync_emails(db)

            if "error" in stats:
                logger.warning(f"Scheduler: sync con aviso: {stats['error']}")
            else:
                logger.info(
                    f"Scheduler sync OK — "
                    f"procesados={stats['processed']}, "
                    f"insertados={stats['inserted']}, "
                    f"omitidos={stats['skipped']}, "
                    f"errores={stats['errors']}"
                )
    except Exception as e:
        logger.error(f"Scheduler: error crítico en sync job: {e}", exc_info=True)


def start_scheduler():
    """Inicia el scheduler con el job de sincronización de Gmail."""
    scheduler.add_job(
        _sync_job,
        trigger=IntervalTrigger(minutes=settings.email_sync_interval_minutes),
        id="gmail_sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        f"Scheduler iniciado — sync automático cada "
        f"{settings.email_sync_interval_minutes} minutos"
    )


def stop_scheduler():
    """Detiene el scheduler limpiamente."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido")
