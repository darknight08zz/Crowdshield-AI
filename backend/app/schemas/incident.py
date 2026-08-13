from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.incident import IncidentStatusEnum


class IncidentBase(BaseModel):
    zone_id: UUID
    type: str
    description: Optional[str] = None
    media_url: Optional[str] = None


class IncidentCreate(IncidentBase):
    pass


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatusEnum


class IncidentResponse(IncidentBase):
    id: UUID
    reporter_id: Optional[UUID] = None
    status: IncidentStatusEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
