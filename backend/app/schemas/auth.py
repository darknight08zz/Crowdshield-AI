from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.user import UserRoleEnum, AccountStatusEnum


class CitizenSignupRequest(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str
    role: Optional[str] = "citizen"


class LoginRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
    user: Dict[str, Any]


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class InviteStaffRequest(BaseModel):
    email: str
    name: str
    role: UserRoleEnum


class InviteStaffResponse(BaseModel):
    invite_id: UUID
    email: str
    name: str
    role: str
    invite_token: str
    invite_link: str
    expires_at: datetime


class AcceptInviteRequest(BaseModel):
    invite_token: str
    password: str
    phone: Optional[str] = None


class RequestResetRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str


class VerifyOTPRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    otp: str
