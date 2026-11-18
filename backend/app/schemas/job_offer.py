from pydantic import BaseModel, HttpUrl, ConfigDict
from datetime import datetime
from typing import Optional


class JobOfferBase(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    platform: Optional[str] = None
    offer_url: Optional[str] = None
    published_at: Optional[datetime] = None
    email_received_at: datetime
    email_message_id: Optional[str] = None


class JobOfferCreate(JobOfferBase):
    """Schema para insertar una oferta (incluye el embedding)."""
    embedding: Optional[list[float]] = None


class JobOfferRead(JobOfferBase):
    """Schema para devolver una oferta al cliente (sin el embedding)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class JobOfferListResponse(BaseModel):
    """Respuesta paginada de ofertas."""
    total: int
    page: int
    page_size: int
    items: list[JobOfferRead]
