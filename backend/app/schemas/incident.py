from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.incident import IncidentStatusEnum


class IncidentTransitionResponse(BaseModel):
    transition_id: str
    incident_id: str
    previous_status: str
    new_status: str
    timestamp: datetime
    actor_type: str
    actor_id: Optional[str] = None
    reason: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class CreationSnapshot(BaseModel):
    source_type: str = Field(default="AI_EARLY_WARNING_PROXY")
    warning_state_at_creation: str = Field(default="EARLY_WARNING")
    physics_risk_at_creation: Optional[float] = None
    ai_probability_at_creation: Optional[float] = None
    telemetry_timestamp: Optional[str] = None
    prediction_timestamp: Optional[str] = None


class LatestSnapshot(BaseModel):
    latest_warning_state: Optional[str] = None
    latest_physics_risk: Optional[float] = None
    latest_ai_probability: Optional[float] = None
    latest_telemetry_timestamp: Optional[str] = None


class IncidentProvenance(BaseModel):
    model_version: str = "v2.0.0"
    prediction_target: str = "EARLY_ESCALATION_5M"
    label_type: str = "PHYSICS_DEFINED_PROXY"
    model_status: str = "PROTOTYPE"
    ground_truth_status: str = "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED"
    generalization_status: str = "INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION"
    disclaimer: str = "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated."


class IncidentCanonicalResponse(BaseModel):
    incident_id: str
    event_id: str
    camera_id: Optional[str] = None
    zone_id: str
    status: str
    source_type: str
    
    creation_snapshot: CreationSnapshot
    latest_snapshot: LatestSnapshot
    
    camera_health_status: Optional[str] = "ONLINE"
    is_stale: bool = False
    is_degraded: bool = False
    
    provenance: IncidentProvenance
    
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_type: Optional[str] = None
    resolution_notes: Optional[str] = None
    
    transitions: List[IncidentTransitionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentTransitionRequest(BaseModel):
    new_status: str = Field(..., description="Target lifecycle state: ACKNOWLEDGED, INVESTIGATING, MITIGATING, RESOLVED, FALSE_POSITIVE")
    reason: Optional[str] = Field(None, description="Optional operator notes or justification")


# Legacy Schemas for Citizen Reporting Endpoint Parity
class IncidentBase(BaseModel):
    zone_id: UUID
    type: str
    description: Optional[str] = None
    media_url: Optional[str] = None


class IncidentCreate(IncidentBase):
    pass


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatusEnum


class IncidentResponse(IncidentBase):
    id: UUID
    reporter_id: Optional[UUID] = None
    status: IncidentStatusEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
