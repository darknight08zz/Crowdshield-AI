from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.models.recommendation import RecommendationStatusEnum


class AIRecommendationBase(BaseModel):
    zone_id: UUID
    risk_score: float = Field(ge=0.0, le=1.0)
    predicted_risk_5min: float = Field(ge=0.0, le=1.0)
    recommended_actions: List[Dict[str, Any]] = Field(default_factory=list)


class AIRecommendationCreate(AIRecommendationBase):
    pass


class AIRecommendationAction(BaseModel):
    status: RecommendationStatusEnum
    edited_announcement: Optional[str] = Field(default=None, description="Operator-edited public announcement text overriding AI draft")
    original_draft_announcement: Optional[str] = Field(default=None, description="Original AI-drafted public announcement text")


class AIRecommendationResponse(AIRecommendationBase):
    id: UUID
    status: RecommendationStatusEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
