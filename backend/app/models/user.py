import enum
from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class UserRoleEnum(str, enum.Enum):
    CITIZEN = "citizen"
    FIELD_OFFICER = "field_officer"
    OPERATOR = "operator"
    EVENT_ADMIN = "event_admin"
    SYSTEM_ADMIN = "system_admin"


class AccountStatusEnum(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    PENDING_VERIFICATION = "pending_verification"
    PENDING_INVITE = "pending_invite"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role = Column(
        SQLEnum(UserRoleEnum, name="user_role", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRoleEnum.CITIZEN
    )
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(50), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    account_status = Column(String(50), default=AccountStatusEnum.ACTIVE.value, nullable=False)
    verification_otp = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
