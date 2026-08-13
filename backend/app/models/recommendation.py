import enum
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class RecommendationStatusEnum(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    MODIFIED = "modified"
    REJECTED = "rejected"


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_score = Column(Float, nullable=False)
    predicted_risk_5min = Column(Float, nullable=False)
    recommended_actions = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    status = Column(
        SQLEnum(RecommendationStatusEnum, name="recommendation_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=RecommendationStatusEnum.PENDING,
        index=True
    )
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
