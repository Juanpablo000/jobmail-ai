from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.sync_service import SyncService
from app.scheduler import scheduler

router = APIRouter(tags=["sync"])
sync_service = SyncService()


@router.post("/sync")
async def trigger_sync(since_days: int = 7, db: AsyncSession = Depends(get_db)):
    """
    Dispara manualmente la sincronización de emails de Gmail.
    Espera a que termine y retorna estadísticas.
    """
    result = await sync_service.sync_emails(db, since_days=since_days)

    if "error" in result and "autenticado" in result.get("error", "").lower():
        raise HTTPException(
            status_code=401,
            detail=result["error"],
        )

    return result


@router.get("/sync/status")
async def sync_status():
    """Estado del scheduler de sincronización automática."""
    is_running = scheduler.running
    next_run = None

    if is_running:
        job = scheduler.get_job("gmail_sync")
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()

    return {
        "scheduler_running": is_running,
        "next_run": next_run,
    }
