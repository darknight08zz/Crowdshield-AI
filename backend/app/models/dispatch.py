import enum
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class OfficerStatusEnum(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


class LocationStatusEnum(str, enum.Enum):
    LOCATION_CURRENT = "LOCATION_CURRENT"
    LOCATION_STALE = "LOCATION_STALE"
    LOCATION_UNKNOWN = "LOCATION_UNKNOWN"


class DispatchStatusEnum(str, enum.Enum):
    UNASSIGNED = "UNASSIGNED"
    ASSIGNED = "ASSIGNED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    RESPONDING = "RESPONDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ResponseOfficer(Base):
    __tablename__ = "response_officers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    officer_id = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(64), nullable=False, default="FIELD_OFFICER")
    status = Column(String(32), nullable=False, default="AVAILABLE", index=True)
    
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)
    location_status = Column(String(32), nullable=False, default="LOCATION_UNKNOWN")
    location_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    assigned_event_id = Column(String(64), nullable=False, default="evt_01", index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    dispatches = relationship("DispatchAssignment", back_populates="officer")


class DispatchAssignment(Base):
    __tablename__ = "dispatch_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispatch_id = Column(String(64), unique=True, index=True, nullable=False)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String(64), nullable=False, default="evt_01")
    officer_id = Column(String(64), ForeignKey("response_officers.officer_id", ondelete="RESTRICT"), nullable=False, index=True)
    
    status = Column(String(32), nullable=False, default="ASSIGNED", index=True)
    assigned_by = Column(String(128), nullable=False)
    assigned_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    en_route_at = Column(DateTime(timezone=True), nullable=True)
    on_scene_at = Column(DateTime(timezone=True), nullable=True)
    responding_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    eta_minutes = Column(Integer, nullable=True, default=5)
    dispatch_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    officer = relationship("ResponseOfficer", back_populates="dispatches")
    transitions = relationship("DispatchTransition", back_populates="dispatch", cascade="all, delete-orphan")


class DispatchTransition(Base):
    __tablename__ = "dispatch_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transition_id = Column(String(64), unique=True, index=True, nullable=False)
    dispatch_id = Column(String(64), ForeignKey("dispatch_assignments.dispatch_id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status = Column(String(32), nullable=False)
    new_status = Column(String(32), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    actor_type = Column(String(32), nullable=False)  # "SYSTEM", "OPERATOR", "FIELD_OFFICER"
    actor_id = Column(String(128), nullable=True)
    reason = Column(Text, nullable=True)
    metadata_json = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    dispatch = relationship("DispatchAssignment", back_populates="transitions")
