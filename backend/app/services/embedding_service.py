"""
EmbeddingService — Hito 2
Genera embeddings de texto usando LM Studio (endpoint OpenAI-compatible).

Modelo: text-embedding-nomic-embed-text-v1.5 (768 dimensiones)
Texto de entrada: "{title} {company} {location} {salary}"

Si LM Studio no está disponible, retorna None y la oferta se inserta
en la BD sin embedding (se puede generar después con un job de backfill).
"""

import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Genera embeddings de texto usando el servidor local de LM Studio."""

    def __init__(self):
        self.base_url = settings.lm_studio_base_url
        self.model = settings.lm_studio_embed_model

    async def embed(self, text: str) -> Optional[list[float]]:
        """
        Genera un vector de 768 dimensiones para el texto dado.

        Args:
            text: Texto a vectorizar (título + empresa + ubicación + salario)

        Returns:
            list[float] con 768 dims, o None si LM Studio no está disponible.
            Las ofertas con embedding=None se insertan igual en la BD.
        """
        if not text or not text.strip():
            logger.warning("Texto vacío para embedding, retornando None")
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    json={
                        "model": self.model,
                        "input": text.strip(),
                    },
                )
                response.raise_for_status()
                data = response.json()
                embedding = data["data"][0]["embedding"]
                logger.debug(f"Embedding generado: {len(embedding)} dims para '{text[:50]}...'")
                return embedding

        except httpx.ConnectError:
            logger.warning(
                f"LM Studio no disponible en {self.base_url}. "
                "Oferta se insertará sin embedding. "
                "Asegúrate de tener LM Studio corriendo con el modelo de embedding cargado."
            )
            return None

        except httpx.TimeoutException:
            logger.warning(f"Timeout al generar embedding (30s). Texto: '{text[:50]}'")
            return None

        except (KeyError, IndexError) as e:
            logger.error(f"Respuesta inesperada de LM Studio: {e}. Response: {response.text[:200]}")
            return None

        except Exception as e:
            logger.warning(f"Error inesperado al generar embedding: {e}")
            return None

    async def embed_batch(self, texts: list[str]) -> list[Optional[list[float]]]:
        """
        Genera embeddings para múltiples textos secuencialmente.
        """
        results = []
        for text in texts:
            embedding = await self.embed(text)
            results.append(embedding)
        return results
