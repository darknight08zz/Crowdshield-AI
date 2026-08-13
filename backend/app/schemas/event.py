from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class EventBase(BaseModel):
    name: str
    date: datetime
    venue: str
    status: str = "upcoming"


class EventCreate(EventBase):
    pass


class EventResponse(EventBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
