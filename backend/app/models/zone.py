from datetime import datetime
import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class Zone(Base):
    __tablename__ = "zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    capacity = Column(Integer, nullable=False)
    current_density = Column(Float, nullable=False, default=0.0)
    risk_score = Column(Float, nullable=False, default=0.0)
    geo_polygon = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    
    # Camera & Spatial Calibration Metadata (Addendum Prompt 2)
    area_m2 = Column(Float, nullable=False, default=500.0)
    calibration_method = Column(String(20), nullable=False, default="area_only")  # "area_only" | "homography"
    homography_matrix = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    reference_points = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    is_calibrated = Column(Float, nullable=False, default=0.0)  # 0.0 = uncalibrated default, 1.0 = calibrated

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
