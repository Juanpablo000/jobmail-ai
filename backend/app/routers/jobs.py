import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job_offer import JobOffer
from app.schemas.job_offer import JobOfferListResponse, JobOfferRead

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=JobOfferListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform: Optional[str] = Query(None, description="linkedin | computrabajo"),
    location: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Búsqueda en título y empresa"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Lista ofertas laborales con filtros y paginación."""
    stmt = select(JobOffer)

    if platform:
        stmt = stmt.where(JobOffer.platform == platform)

    if location:
        stmt = stmt.where(JobOffer.location.ilike(f"%{location}%"))

    if search:
        stmt = stmt.where(
            or_(
                JobOffer.title.ilike(f"%{search}%"),
                JobOffer.company.ilike(f"%{search}%"),
            )
        )

    if date_from:
        stmt = stmt.where(JobOffer.email_received_at >= date_from)

    if date_to:
        stmt = stmt.where(JobOffer.email_received_at <= date_to)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.order_by(JobOffer.email_received_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return JobOfferListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/jobs/export/csv")
async def export_jobs_csv(
    platform: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Exporta todas las ofertas laborales registradas a un archivo CSV estructurado (UTF-8 con BOM para Excel).
    """
    stmt = select(JobOffer).order_by(JobOffer.email_received_at.desc())
    if platform:
        stmt = stmt.where(JobOffer.platform == platform)

    result = await db.execute(stmt)
    offers = result.scalars().all()

    output = io.StringIO()
    # Escribir BOM para que Microsoft Excel lo abra con tildes y caracteres en español correctamente
    output.write("\ufeff")

    writer = csv.writer(output, delimiter=",", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "ID",
        "Título",
        "Empresa",
        "Ubicación",
        "Salario",
        "Plataforma",
        "URL Oferta",
        "Fecha Publicación",
        "Fecha Correo Gmail",
        "Fecha Registro Sistema",
    ])

    for o in offers:
        pub_date = o.published_at.strftime("%Y-%m-%d %H:%M") if o.published_at else ""
        rec_date = o.email_received_at.strftime("%Y-%m-%d %H:%M") if o.email_received_at else ""
        created_date = o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else ""

        writer.writerow([
            o.id,
            o.title or "",
            o.company or "",
            o.location or "",
            o.salary or "",
            o.platform or "",
            o.offer_url or "",
            pub_date,
            rec_date,
            created_date,
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=ofertas_laborales.csv",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


@router.get("/jobs/{job_id}", response_model=JobOfferRead)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Retorna el detalle de una oferta por ID."""
    result = await db.execute(select(JobOffer).where(JobOffer.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")
    return job
