from sqlalchemy import String, Text, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from datetime import datetime
from app.database import Base


class JobOffer(Base):
    """
    Oferta laboral extraída de un correo de Gmail.

    Campos de la oferta (parseados del correo):
        title, company, location, salary, platform, offer_url, published_at

    Campos del correo (metadata de Gmail):
        email_received_at, email_message_id

    Nota: el HTML crudo del correo NO se guarda en BD.
    Se usa solo en memoria durante el parsing y se descarta.
    Si necesitas re-parsear, usa email_message_id para volver a buscarlo en Gmail.
    """

    __tablename__ = "job_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Datos de la oferta ────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    salary: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 'linkedin' | 'computrabajo' | 'otro'
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    offer_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Fecha de publicación de la oferta (si viene en el correo)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # ── Metadata del correo ───────────────────────────────────────────────────
    # Fecha en que llegó el correo a Gmail
    email_received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    # Gmail message ID — indexado para deduplicación, pero NO unique:
    # un email puede contener múltiples ofertas (varias filas con el mismo message_id)
    # Deduplicación: se verifica en SyncService antes de procesar cada email
    email_message_id: Mapped[str | None] = mapped_column(
        String(255), unique=False, nullable=True, index=True
    )

    # ── Búsqueda semántica ────────────────────────────────────────────────────
    # Vector de 768 dims (nomic-embed-text-v1.5)
    # Se genera concatenando: "{title} {company} {location} {salary}"
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<JobOffer id={self.id} title={self.title!r} platform={self.platform!r}>"
