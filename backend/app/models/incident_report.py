import enum
from datetime import datetime
import uuid
from typing import Dict, Set
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class IncidentReportStatusEnum(str, enum.Enum):
    REPORT_SUBMITTED = "REPORT_SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


# Canonical explicit transition map for IncidentReport
VALID_INCIDENT_REPORT_TRANSITIONS: Dict[str, Set[str]] = {
    IncidentReportStatusEnum.REPORT_SUBMITTED.value: {
        IncidentReportStatusEnum.UNDER_REVIEW.value,
        IncidentReportStatusEnum.ACCEPTED.value,
        IncidentReportStatusEnum.REJECTED.value,
    },
    IncidentReportStatusEnum.UNDER_REVIEW.value: {
        IncidentReportStatusEnum.ACCEPTED.value,
        IncidentReportStatusEnum.REJECTED.value,
    },
    IncidentReportStatusEnum.ACCEPTED.value: set(),
    IncidentReportStatusEnum.REJECTED.value: set(),
}


class IncidentReport(Base):
    __tablename__ = "incident_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(String(64), unique=True, index=True, nullable=False)
    event_id = Column(String(64), index=True, nullable=False)
    zone_id = Column(String(64), nullable=True)
    camera_id = Column(String(64), nullable=True)

    submitted_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    submitted_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    status = Column(String(32), nullable=False, default="REPORT_SUBMITTED", index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    reported_location = Column(String(255), nullable=True)
    report_source = Column(String(64), nullable=False, default="VIEWER")
    media_url = Column(Text, nullable=True)

    reviewed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_reason = Column(Text, nullable=True)

    accepted_incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    submitter = relationship("User", foreign_keys=[submitted_by_user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by_user_id])
    accepted_incident = relationship("Incident", foreign_keys=[accepted_incident_id])
