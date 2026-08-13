from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.models.gate import GateTypeEnum, GateStatusEnum


class GateBase(BaseModel):
    event_id: UUID
    zone_id: Optional[UUID] = None
    name: str
    type: GateTypeEnum = GateTypeEnum.ENTRY
    capacity_per_min: int = Field(ge=0, default=100)
    status: GateStatusEnum = GateStatusEnum.OPEN


class GateCreate(GateBase):
    pass


class GateStatusUpdate(BaseModel):
    status: GateStatusEnum


class GateResponse(GateBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
