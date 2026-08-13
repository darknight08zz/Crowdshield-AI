import enum
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class AssignmentStatusEnum(str, enum.Enum):
    ASSIGNED = "assigned"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OfficerAssignment(Base):
    __tablename__ = "officer_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    officer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True)
    task_description = Column(Text, nullable=False)
    status = Column(
        SQLEnum(AssignmentStatusEnum, name="assignment_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=AssignmentStatusEnum.ASSIGNED,
        index=True
    )
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
