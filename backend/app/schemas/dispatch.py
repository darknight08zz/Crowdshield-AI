from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ResponseOfficerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    officer_id: str
    user_id: Optional[str] = None
    name: str
    role: str = "FIELD_OFFICER"
    status: str = "AVAILABLE"  # AVAILABLE, ASSIGNED, BUSY, OFFLINE
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    location_status: str = "LOCATION_UNKNOWN"  # LOCATION_CURRENT, LOCATION_STALE, LOCATION_UNKNOWN
    location_timestamp: Optional[datetime] = None
    assigned_event_id: str = "evt_01"
    created_at: datetime
    updated_at: datetime


class DispatchCreateRequest(BaseModel):
    officer_id: str = Field(..., description="ID of the field officer to assign")
    eta_minutes: Optional[int] = Field(default=5, ge=1, le=180, description="Estimated time of arrival in minutes")
    reason: str = Field(..., min_length=3, description="Mandatory dispatch operational justification reason")


class DispatchTransitionRequest(BaseModel):
    new_status: str = Field(..., description="Target status: ACKNOWLEDGED, EN_ROUTE, ON_SCENE, RESPONDING, COMPLETED, CANCELLED")
    reason: Optional[str] = Field(None, description="Optional operational notes or reason for status transition")


class DispatchTransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transition_id: str
    dispatch_id: str
    previous_status: str
    new_status: str
    timestamp: datetime
    actor_type: str
    actor_id: Optional[str] = None
    reason: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class DispatchCanonicalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dispatch_id: str
    incident_id: str
    event_id: str
    officer_id: str
    status: str
    assigned_by: str
    assigned_at: datetime
    acknowledged_at: Optional[datetime] = None
    en_route_at: Optional[datetime] = None
    on_scene_at: Optional[datetime] = None
    responding_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    eta_minutes: Optional[int] = None
    dispatch_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    officer: Optional[ResponseOfficerResponse] = None
    transitions: List[DispatchTransitionResponse] = []


class FieldOfficerAssignmentContextResponse(BaseModel):
    dispatch: DispatchCanonicalResponse
    incident_id: str
    zone_id: str
    event_id: str
    camera_id: Optional[str] = None
    warning_state: str
    physics_risk: Optional[float] = None
    ai_probability: Optional[float] = None
    model_version: str = "v2.0.0"
    label_type: str = "PHYSICS_DEFINED_PROXY"
    model_status: str = "PROTOTYPE"
    disclaimer: str = "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated."
