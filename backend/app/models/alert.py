import enum
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class AlertSeverityEnum(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    severity = Column(
        SQLEnum(AlertSeverityEnum, name="alert_severity", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=AlertSeverityEnum.MEDIUM
    )
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
