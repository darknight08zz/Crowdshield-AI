from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class ZoneBase(BaseModel):
    event_id: UUID
    name: str
    capacity: int = Field(gt=0, description="Maximum occupant capacity of zone")
    current_density: float = Field(ge=0.0, default=0.0)
    risk_score: float = Field(ge=0.0, le=1.0, default=0.0)
    geo_polygon: Optional[Dict[str, Any]] = None


class ZoneCreate(ZoneBase):
    pass


class ZoneUpdateDensity(BaseModel):
    current_density: float = Field(ge=0.0)
    risk_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ZoneResponse(ZoneBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ZoneAdjacencyBase(BaseModel):
    event_id: UUID
    zone_a_id: UUID
    zone_b_id: UUID
    connection_type: str = "open_path"
    connection_capacity: float = 100.0
    vector_direction: Optional[str] = "bidirectional"


class ZoneAdjacencyCreate(ZoneAdjacencyBase):
    pass


class ZoneAdjacencyResponse(ZoneAdjacencyBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ZoneRiskResponse(BaseModel):
    zone_id: UUID
    current_risk: float
    risk_2min: float
    risk_5min: float
    risk_10min: float
    risk_level: str
    risk_bucket: str
    risk_source: str = "independent"
    propagated_from_zone_id: Optional[str] = None
    propagated_from_zone_name: Optional[str] = None
    behavior_pattern: str
    trajectory_trend: str
    trajectory_warning: str
    explanation: Dict[str, Any]
    propagation: Optional[Dict[str, Any]] = None
    feature_vector: Dict[str, float]
    updated_at: datetime

