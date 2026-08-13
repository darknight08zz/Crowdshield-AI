from datetime import datetime
import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class ZoneMetricsHistory(Base):
    __tablename__ = "zone_metrics_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    density = Column(Float, nullable=False, default=0.0)
    inflow_rate = Column(Float, nullable=False, default=0.0)
    outflow_rate = Column(Float, nullable=False, default=0.0)
    avg_speed = Column(Float, nullable=False, default=1.2)
    risk_score = Column(Float, nullable=False, default=0.0)
    behavior_classification = Column(String(64), nullable=False, default="NORMAL")
    propagated_risk_score = Column(Float, nullable=True, default=0.0)

    __table_args__ = (
        Index("idx_zone_metrics_zone_time", "zone_id", "timestamp"),
        Index("idx_zone_metrics_event_time", "event_id", "timestamp"),
    )
