from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_role = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    target = Column(String(255), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(255), nullable=True)
    event_id = Column(String(100), nullable=True, index=True)
    camera_id = Column(String(100), nullable=True)
    zone_id = Column(String(100), nullable=True)
    before_state = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    after_state = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    reason = Column(String(500), nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    failure_code = Column(String(50), nullable=True)
    request_id = Column(String(100), nullable=True, index=True)
    source = Column(String(100), default="API", nullable=False)
    metadata_json = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

