from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.audit import AuditLog


def log_action(
    db: Session,
    actor_id: Optional[UUID],
    action: str,
    target: str,
    before_state: Optional[Dict[str, Any]] = None,
    after_state: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Persists an audit log record for security, operational auditability, and compliance.
    """
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        target=target,
        before_state=before_state,
        after_state=after_state
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
