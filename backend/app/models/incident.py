import enum
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class IncidentStatusEnum(str, enum.Enum):
    REPORTED = "reported"
    VERIFIED = "verified"
    FALSE_ALARM = "false_alarm"
    RESOLVED = "resolved"


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    media_url = Column(Text, nullable=True)
    status = Column(
        SQLEnum(IncidentStatusEnum, name="incident_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=IncidentStatusEnum.REPORTED,
        index=True
    )
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
