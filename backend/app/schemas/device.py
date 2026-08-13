from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class DeviceTokenRegister(BaseModel):
    fcm_token: str = Field(..., description="Firebase Cloud Messaging Device Registration Token")
    platform: str = Field("android", description="Device platform (android, ios, web)")


class DeviceTokenResponse(BaseModel):
    id: UUID
    user_id: UUID
    fcm_token: str
    platform: str
    updated_at: datetime

    class Config:
        from_attributes = True
