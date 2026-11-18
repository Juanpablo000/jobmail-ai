from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.rag_service import RAGService

router = APIRouter(tags=["chat"])
rag_service = RAGService()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("/chat")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Endpoint de chat conversacional con el agente local de LM Studio.
    Realiza búsqueda semántica y de palabras clave en PostgreSQL, y responde
    mediante Server-Sent Events (SSE) en tiempo real.
    """
    return StreamingResponse(
        rag_service.stream_response(db, request.message, request.history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
