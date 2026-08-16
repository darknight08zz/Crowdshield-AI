import enum
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class IncidentStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    MITIGATING = "MITIGATING"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"

    # Backward compatibility aliases
    REPORTED = "REPORTED"
    VERIFIED = "VERIFIED"
    FALSE_ALARM = "FALSE_ALARM"


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(String(64), unique=True, index=True, nullable=False)
    event_id = Column(String(64), index=True, nullable=False, default="evt_01")
    camera_id = Column(String(64), index=True, nullable=True)
    zone_id = Column(String(64), index=True, nullable=False)

    # Legacy fields for citizen reporting compatibility
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(String(50), nullable=True, default="SAFETY_SURGE")
    description = Column(Text, nullable=True)
    media_url = Column(Text, nullable=True)

    # Core Incident Lifecycle Status
    status = Column(String(32), nullable=False, default="OPEN", index=True)

    # Source & Creation Snapshot
    source_type = Column(String(64), nullable=False, default="AI_EARLY_WARNING_PROXY")
    warning_state_at_creation = Column(String(32), nullable=False, default="EARLY_WARNING")
    physics_risk_at_creation = Column(Float, nullable=True)
    ai_probability_at_creation = Column(Float, nullable=True)
    telemetry_timestamp = Column(String(64), nullable=True)
    prediction_timestamp = Column(String(64), nullable=True)

    # Dynamic Latest Context
    latest_warning_state = Column(String(32), nullable=True)
    latest_physics_risk = Column(Float, nullable=True)
    latest_ai_probability = Column(Float, nullable=True)
    latest_telemetry_timestamp = Column(String(64), nullable=True)

    # Health & Quality Indicators
    camera_health_status = Column(String(32), nullable=True, default="ONLINE")
    is_stale = Column(Boolean, nullable=False, default=False)
    is_degraded = Column(Boolean, nullable=False, default=False)

    # Mandatory AI Provenance
    model_version = Column(String(32), nullable=False, default="v2.0.0")
    prediction_target = Column(String(64), nullable=False, default="EARLY_ESCALATION_5M")
    label_type = Column(String(64), nullable=False, default="PHYSICS_DEFINED_PROXY")
    model_status = Column(String(32), nullable=False, default="PROTOTYPE")
    ground_truth_status = Column(String(128), nullable=False, default="NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED")
    generalization_status = Column(String(128), nullable=False, default="INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION")
    disclaimer = Column(Text, nullable=False, default="AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.")

    # Operator Information & Actions
    acknowledged_by = Column(String(128), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(128), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_type = Column(String(64), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    transitions = relationship("IncidentTransition", back_populates="incident", cascade="all, delete-orphan")


class IncidentTransition(Base):
    __tablename__ = "incident_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transition_id = Column(String(64), unique=True, index=True, nullable=False)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status = Column(String(32), nullable=False)
    new_status = Column(String(32), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    actor_type = Column(String(32), nullable=False)  # "SYSTEM" or "OPERATOR"
    actor_id = Column(String(128), nullable=True)
    reason = Column(Text, nullable=True)
    metadata_json = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    incident = relationship("Incident", back_populates="transitions")
