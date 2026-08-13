from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    venue = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="upcoming")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
