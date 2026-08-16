from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.audit import AuditLog


def log_action(
    db: Session,
    actor_id: Optional[UUID] = None,
    action: str = "UNKNOWN_ACTION",
    target: str = "UNKNOWN_TARGET",
    before_state: Optional[Dict[str, Any]] = None,
    after_state: Optional[Dict[str, Any]] = None,
    actor_role: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    event_id: Optional[str] = None,
    camera_id: Optional[str] = None,
    zone_id: Optional[str] = None,
    reason: Optional[str] = None,
    success: bool = True,
    failure_code: Optional[str] = None,
    request_id: Optional[str] = None,
    source: str = "API",
    metadata_json: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Persists an audit log record for security, operational auditability, and compliance.
    """
    entry = AuditLog(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        target=target,
        resource_type=resource_type,
        resource_id=resource_id,
        event_id=event_id,
        camera_id=camera_id,
        zone_id=zone_id,
        before_state=before_state,
        after_state=after_state,
        reason=reason,
        success=success,
        failure_code=failure_code,
        request_id=request_id,
        source=source,
        metadata_json=metadata_json
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_audit_logs(
    db: Session,
    actor_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    event_id: Optional[str] = None,
    success: Optional[bool] = None,
    request_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[AuditLog]:
    """
    Retrieves filtered audit log records in reverse chronological order.
    """
    query = db.query(AuditLog)
    if actor_id:
        try:
            val_uuid = UUID(str(actor_id))
            query = query.filter(AuditLog.actor_id == val_uuid)
        except Exception:
            pass
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.filter(AuditLog.resource_id == resource_id)
    if event_id:
        query = query.filter(AuditLog.event_id == event_id)
    if success is not None:
        query = query.filter(AuditLog.success == success)
    if request_id:
        query = query.filter(AuditLog.request_id == request_id)

    return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()
