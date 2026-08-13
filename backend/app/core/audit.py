from typing import Optional, Dict, Any, Union
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.audit import AuditLog


def log_audit_event(
    db: Session,
    action: str,
    target: str,
    actor_id: Optional[Union[UUID, str]] = None,
    before_state: Optional[Dict[str, Any]] = None,
    after_state: Optional[Dict[str, Any]] = None
):
    """
    Utility for inserting compliance audit log records.
    """
    try:
        parsed_actor_id = None
        if actor_id:
            try:
                parsed_actor_id = UUID(str(actor_id))
            except Exception:
                parsed_actor_id = None

        audit_entry = AuditLog(
            actor_id=parsed_actor_id,
            action=action,
            target=target,
            before_state=before_state,
            after_state=after_state
        )
        db.add(audit_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[AUDIT LOG WARNING] Failed to record audit log: {e}")
