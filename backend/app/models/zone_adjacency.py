import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.core.database import Base


class ConnectionType(str, enum.Enum):
    GATE = "gate"
    OPEN_PATH = "open_path"
    CORRIDOR = "corridor"


class ZoneAdjacency(Base):
    __tablename__ = "zone_adjacencies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    zone_a_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True)
    zone_b_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True)
    
    connection_type = Column(
        SQLEnum(ConnectionType, name="connection_type_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ConnectionType.OPEN_PATH
    )
    connection_capacity = Column(Float, nullable=False, default=100.0)  # capacity multiplier / peds per min
    vector_direction = Column(String(50), nullable=True, default="bidirectional")  # e.g., "A_to_B", "B_to_A", "bidirectional"
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
