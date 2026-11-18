"""
RAGService — Hito 4
Motor RAG (Retrieval-Augmented Generation) para consultar ofertas laborales con LM Studio.

Flujo de consulta:
  1. Recibe la pregunta del usuario (ej: "¿Qué ofertas hay de trainee en analítica de datos?")
  2. Búsqueda Híbrida en PostgreSQL:
     - Búsqueda vectorial (pgvector <=> distancia coseno) si el embedding está disponible
     - Búsqueda por palabras clave (ILIKE / Full-text) para capturar coincidencias exactas
  3. Combina y rankea los resultados más relevantes
  4. Arma un contexto estructurado en formato Markdown / JSON
  5. Envía la solicitud con streaming a LM Studio (http://localhost:1234/v1/chat/completions)
  6. Emite los tokens en tiempo real mediante Server-Sent Events (SSE)
"""

import json
import logging
from typing import AsyncGenerator, Optional
import httpx
from sqlalchemy import select, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.job_offer import JobOffer
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Eres el Asistente Inteligente de JobMail AI.
Tu misión es ayudar al usuario a encontrar y analizar ofertas de empleo guardadas en su base de datos personal.

REGLAS DE RESPUESTA:
1. Responde SIEMPRE en español, de forma clara, profesional y concisa.
2. Basa tus respuestas ÚNICAMENTE en las ofertas que se te proporcionan en el CONTEXTO.
3. Si encuentras ofertas relevantes, menciona claramente:
   - 📌 Título del puesto
   - 🏢 Empresa
   - 📍 Ubicación / Modalidad (si aplica)
   - 💰 Salario (si está disponible)
   - 🌐 Plataforma (LinkedIn o Computrabajo)
   - 🔗 Enlace directo (si está disponible)
4. Si ninguna oferta del contexto coincide con lo que busca el usuario, indícalo amablemente y sugiérele ampliar su búsqueda o esperar a nuevas alertas de correo.
5. NO inventes información, empresas, salarios ni enlaces que no estén explícitamente en el contexto.
"""


class RAGService:
    def __init__(self):
        self.embedder = EmbeddingService()
        self.lm_studio_url = settings.lm_studio_base_url
        self.chat_model = settings.lm_studio_chat_model

    async def retrieve_relevant_jobs(
        self, db: AsyncSession, query: str, limit: int = 8
    ) -> list[JobOffer]:
        """
        Búsqueda híbrida (vectorial + keywords) en la base de datos de ofertas.
        """
        results: dict[int, JobOffer] = {}

        # 1. Búsqueda Semántica por Vectores (pgvector)
        query_embedding = await self.embedder.embed(query)
        if query_embedding:
            try:
                # pgvector cosine distance operator: <=>
                vector_str = "[" + ",".join(str(f) for f in query_embedding) + "]"
                stmt = (
                    select(JobOffer)
                    .where(JobOffer.embedding.is_not(None))
                    .order_by(text(f"embedding <=> '{vector_str}'"))
                    .limit(limit)
                )
                res = await db.execute(stmt)
                for job in res.scalars().all():
                    results[job.id] = job
            except Exception as e:
                logger.warning(f"Error en búsqueda vectorial: {e}")

        # 2. Búsqueda por Palabras Clave (fallback / complemento para términos técnicos)
        # Extraer tokens significativos (> 2 letras)
        clean_tokens = [t for t in query.replace("?", "").replace("¿", "").split() if len(t) > 2]
        if clean_tokens:
            ilike_conditions = []
            for token in clean_tokens[:5]:
                ilike_conditions.append(JobOffer.title.ilike(f"%{token}%"))
                ilike_conditions.append(JobOffer.company.ilike(f"%{token}%"))
                ilike_conditions.append(JobOffer.location.ilike(f"%{token}%"))

            stmt_kw = (
                select(JobOffer)
                .where(or_(*ilike_conditions))
                .order_by(JobOffer.email_received_at.desc())
                .limit(limit)
            )
            res_kw = await db.execute(stmt_kw)
            for job in res_kw.scalars().all():
                if job.id not in results:
                    results[job.id] = job

        # 3. Fallback: Si no hay resultados de búsqueda, traer las últimas ofertas registradas
        if not results:
            stmt_recent = (
                select(JobOffer)
                .order_by(JobOffer.email_received_at.desc())
                .limit(5)
            )
            res_recent = await db.execute(stmt_recent)
            for job in res_recent.scalars().all():
                results[job.id] = job

        return list(results.values())[:limit]

    def build_prompt_context(self, jobs: list[JobOffer]) -> str:
        """Formatea las ofertas como contexto en lenguaje claro para el modelo."""
        if not jobs:
            return "No se encontraron ofertas almacenadas en la base de datos."

        lines = ["OFERTAS DISPONIBLES EN TU BASE DE DATOS:"]
        for i, j in enumerate(jobs, 1):
            received = j.email_received_at.strftime("%Y-%m-%d") if j.email_received_at else "No especificada"
            lines.append(
                f"\n--- OFERTA #{i} ---"
                f"\n• Título: {j.title}"
                f"\n• Empresa: {j.company or 'Confidencial / No especificada'}"
                f"\n• Ubicación: {j.location or 'No especificada'}"
                f"\n• Salario: {j.salary or 'No especificado'}"
                f"\n• Plataforma: {j.platform or 'No especificada'}"
                f"\n• Fecha de correo: {received}"
                f"\n• URL: {j.offer_url or 'Sin enlace directo'}"
            )
        return "\n".join(lines)

    async def stream_response(
        self, db: AsyncSession, user_message: str, history: list[dict]
    ) -> AsyncGenerator[str, None]:
        """
        Generador asíncrono que transmite la respuesta en tiempo real en formato SSE.
        """
        try:
            # 1. Recuperar ofertas relevantes
            relevant_jobs = await self.retrieve_relevant_jobs(db, user_message)
            context = self.build_prompt_context(relevant_jobs)

            # 2. Construir la lista de mensajes para el LLM
            messages = [{"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{context}"}]

            # Añadir historial reciente (últimos 4 mensajes para contexto de conversación)
            for msg in history[-4:]:
                if msg.get("role") in ["user", "assistant"] and msg.get("content"):
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"],
                    })

            # Añadir el mensaje actual del usuario si no está en el historial
            if not history or history[-1].get("content") != user_message:
                messages.append({"role": "user", "content": user_message})

            # 3. Llamar a LM Studio con streaming activado
            async with httpx.AsyncClient(timeout=120.0) as client:
                try:
                    async with client.stream(
                        "POST",
                        f"{self.lm_studio_url}/chat/completions",
                        json={
                            "model": self.chat_model,
                            "messages": messages,
                            "temperature": 0.3,
                            "stream": True,
                        },
                    ) as response:
                        if response.status_code != 200:
                            err_body = await response.aread()
                            yield f"data: ⚠️ Error de LM Studio ({response.status_code}): {err_body.decode('utf-8', errors='ignore')}\n\n"
                            yield "data: [DONE]\n\n"
                            return

                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    yield "data: [DONE]\n\n"
                                    break
                                try:
                                    payload = json.loads(data_str)
                                    delta = payload.get("choices", [{}])[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        # Escapar saltos de línea para el protocolo SSE
                                        yield f"data: {content}\n\n"
                                except json.JSONDecodeError:
                                    continue

                except httpx.ConnectError:
                    yield (
                        f"data: 🔌 No se pudo conectar con LM Studio en {self.lm_studio_url}.\n\n"
                    )
                    yield (
                        f"data: 👉 Asegúrate de abrir LM Studio, iniciar el servidor local en el puerto 1234 y cargar el modelo '{self.chat_model}'.\n\n"
                    )
                    yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Error en RAG stream: {e}", exc_info=True)
            yield f"data: ⚠️ Error procesando la consulta: {str(e)}\n\n"
            yield "data: [DONE]\n\n"
