"""
SyncService — Hito 2
Orquesta el proceso completo de sincronización:
  1. Obtiene emails de Gmail (GmailService)
  2. Parsea HTML en memoria -> ParsedOffer[] (ParserService)
  3. Genera embeddings (EmbeddingService) — opcional, None si LM Studio no disponible
  4. Inserta en PostgreSQL (deduplicando por email_message_id y offer_url)

DEDUPLICACIÓN:
  - Por email: si ya existe alguna oferta con ese email_message_id -> skip email completo
  - Por oferta: si ya existe offer_url en la BD -> skip esa oferta individual
"""

import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_offer import JobOffer
from app.services.gmail_service import GmailService, TOKEN_PATH
from app.services.parser_service import ParserService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class SyncService:
    """Orquesta la sincronización completa de emails -> base de datos."""

    def __init__(self):
        self.gmail = GmailService()
        self.parser = ParserService()
        self.embedder = EmbeddingService()

    async def sync_emails(self, db: AsyncSession, since_days: int = 7) -> dict:
        """
        Sincroniza emails de ofertas laborales de Gmail a la BD.

        Returns:
            dict con stats: {
                "processed": int,
                "inserted": int,
                "skipped": int,
                "errors": int,
                "no_embedding": int
            }
        """
        stats = {
            "processed": 0,
            "inserted": 0,
            "skipped": 0,
            "errors": 0,
            "no_embedding": 0,
        }

        if not TOKEN_PATH.exists():
            logger.warning("Gmail no autenticado. Visita /auth/login")
            return {
                **stats,
                "error": "Gmail no autenticado. Visita http://localhost:8000/auth/login",
            }

        try:
            emails = await self.gmail.fetch_job_emails(since_days=since_days)
        except FileNotFoundError as e:
            logger.error(f"Error de autenticación: {e}")
            return {**stats, "error": str(e)}
        except Exception as e:
            logger.error(f"Error al obtener emails de Gmail: {e}", exc_info=True)
            return {**stats, "error": f"Error Gmail: {e}"}

        logger.info(f"Sync iniciado: {len(emails)} emails obtenidos")

        for email_data in emails:
            stats["processed"] += 1
            msg_id = email_data["message_id"]

            try:
                already_processed = await self._email_already_processed(db, msg_id)
                if already_processed:
                    logger.debug(f"Email {msg_id} ya procesado, omitiendo")
                    stats["skipped"] += 1
                    continue

                parsed_offers = self.parser.parse(
                    html_body=email_data["html_body"],
                    platform=email_data["platform"],
                    email_received_at=email_data["received_at"],
                )

                if not parsed_offers:
                    logger.warning(f"Email {msg_id} ({email_data['platform']}): sin ofertas extraídas")
                    stats["errors"] += 1
                    continue

                logger.info(f"Email {msg_id}: {len(parsed_offers)} ofertas parseadas")

                inserted_in_email = 0
                for offer in parsed_offers:
                    if offer.offer_url:
                        url_exists = await self._url_already_exists(db, offer.offer_url)
                        if url_exists:
                            logger.debug(f"URL ya existe: {offer.offer_url[:60]}")
                            stats["skipped"] += 1
                            continue

                    text_to_embed = " ".join(filter(None, [
                        offer.title,
                        offer.company,
                        offer.location,
                        offer.salary,
                    ])).strip()

                    embedding = await self.embedder.embed(text_to_embed)
                    if embedding is None:
                        stats["no_embedding"] += 1

                    job = JobOffer(
                        title=offer.title,
                        company=offer.company,
                        location=offer.location,
                        salary=offer.salary,
                        platform=offer.platform,
                        offer_url=offer.offer_url,
                        published_at=offer.published_at,
                        email_received_at=email_data["received_at"],
                        email_message_id=msg_id,
                        embedding=embedding,
                    )
                    db.add(job)
                    inserted_in_email += 1
                    stats["inserted"] += 1

                await db.commit()
                logger.info(f"Email {msg_id}: {inserted_in_email} ofertas insertadas")

            except Exception as e:
                logger.error(f"Error procesando email {msg_id}: {e}", exc_info=True)
                await db.rollback()
                stats["errors"] += 1
                continue

        logger.info(
            f"Sync completado: {stats['processed']} emails, "
            f"{stats['inserted']} ofertas nuevas, "
            f"{stats['skipped']} omitidas, "
            f"{stats['errors']} errores, "
            f"{stats['no_embedding']} sin embedding"
        )
        return stats

    async def _email_already_processed(self, db: AsyncSession, message_id: str) -> bool:
        result = await db.execute(
            select(func.count()).select_from(JobOffer).where(
                JobOffer.email_message_id == message_id
            )
        )
        count = result.scalar_one()
        return count > 0

    async def _url_already_exists(self, db: AsyncSession, url: str) -> bool:
        result = await db.execute(
            select(func.count()).select_from(JobOffer).where(
                JobOffer.offer_url == url
            )
        )
        count = result.scalar_one()
        return count > 0
