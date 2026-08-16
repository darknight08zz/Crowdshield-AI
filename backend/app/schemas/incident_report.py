from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class IncidentReportCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Brief summary of the observed issue")
    description: str = Field(..., min_length=5, description="Detailed description of the incident/observation")
    event_id: Optional[str] = Field("evt_01", description="Event identifier")
    zone_id: Optional[str] = Field(None, description="Zone identifier if known")
    camera_id: Optional[str] = Field(None, description="Camera identifier if relevant")
    reported_location: Optional[str] = Field(None, description="Geospatial or location context")
    media_url: Optional[str] = Field(None, description="Optional image/media reference URL")


class IncidentReportReview(BaseModel):
    status: str = Field(..., description="Target review status: UNDER_REVIEW, ACCEPTED, or REJECTED")
    review_reason: Optional[str] = Field(None, description="Review notes or justification (Required for REJECTED)")


class IncidentReportResponse(BaseModel):
    id: UUID
    report_id: str
    event_id: str
    zone_id: Optional[str] = None
    camera_id: Optional[str] = None
    submitted_by_user_id: UUID
    submitted_at: datetime
    status: str
    title: str
    description: str
    reported_location: Optional[str] = None
    report_source: str = "VIEWER"
    media_url: Optional[str] = None
    reviewed_by_user_id: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    review_reason: Optional[str] = None
    accepted_incident_id: Optional[UUID] = None
    accepted_incident_human_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncidentReportListResponse(BaseModel):
    items: List[IncidentReportResponse]
    total: int
