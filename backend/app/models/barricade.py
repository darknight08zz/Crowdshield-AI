import enum
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class BarricadeConfigurationEnum(str, enum.Enum):
    OPEN = "open"
    NARROW = "narrow"
    CLOSED = "closed"
    REDIRECT_LEFT = "redirect_left"
    REDIRECT_RIGHT = "redirect_right"


class Barricade(Base):
    __tablename__ = "barricades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    position_geometry = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    current_configuration = Column(
        SQLEnum(BarricadeConfigurationEnum, name="barricade_config", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=BarricadeConfigurationEnum.OPEN
    )
    moveable = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
