from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models.user import UserRoleEnum, AccountStatusEnum


class UserBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: UserRoleEnum = UserRoleEnum.CITIZEN
    account_status: Optional[str] = AccountStatusEnum.ACTIVE.value
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    id: Optional[UUID] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
