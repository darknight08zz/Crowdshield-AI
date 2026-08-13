import enum
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class GateTypeEnum(str, enum.Enum):
    ENTRY = "entry"
    EXIT = "exit"
    EMERGENCY = "emergency"
    BIDIRECTIONAL = "bidirectional"


class GateStatusEnum(str, enum.Enum):
    OPEN = "open"
    RESTRICTED = "restricted"
    CLOSED = "closed"


class Gate(Base):
    __tablename__ = "gates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(
        SQLEnum(GateTypeEnum, name="gate_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=GateTypeEnum.ENTRY
    )
    capacity_per_min = Column(Integer, nullable=False, default=100)
    status = Column(
        SQLEnum(GateStatusEnum, name="gate_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=GateStatusEnum.OPEN
    )
    # Virtual Line Definition (Addendum Prompt 3): [[x1, y1], [x2, y2]] in camera frame space
    virtual_line = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
