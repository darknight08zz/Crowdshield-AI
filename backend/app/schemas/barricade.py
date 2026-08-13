from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.barricade import BarricadeConfigurationEnum


class BarricadeBase(BaseModel):
    event_id: UUID
    zone_id: Optional[UUID] = None
    name: str
    position_geometry: Optional[Any] = None
    current_configuration: BarricadeConfigurationEnum = BarricadeConfigurationEnum.OPEN
    moveable: bool = True


class BarricadeCreate(BarricadeBase):
    pass


class BarricadeConfigUpdate(BaseModel):
    current_configuration: BarricadeConfigurationEnum


class BarricadeResponse(BarricadeBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
