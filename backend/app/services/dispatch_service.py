import logging
from datetime import datetime, timezone
import uuid
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.dispatch import (
    ResponseOfficer,
    DispatchAssignment,
    DispatchTransition,
    OfficerStatusEnum,
    LocationStatusEnum,
    DispatchStatusEnum,
)
from app.models.user import User, UserRoleEnum

logger = logging.getLogger("crowdshield.services.dispatch")

VALID_DISPATCH_TRANSITIONS: Dict[str, set] = {
    "UNASSIGNED": {"ASSIGNED"},
    "ASSIGNED": {"ACKNOWLEDGED", "CANCELLED"},
    "ACKNOWLEDGED": {"EN_ROUTE", "CANCELLED"},
    "EN_ROUTE": {"ON_SCENE", "CANCELLED"},
    "ON_SCENE": {"RESPONDING", "CANCELLED"},
    "RESPONDING": {"COMPLETED", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}

DEFAULT_OFFICERS = [
    {
        "officer_id": "FO-001",
        "name": "Officer Rahul Sharma",
        "role": "FIELD_OFFICER",
        "status": "AVAILABLE",
        "current_latitude": 28.6139,
        "current_longitude": 77.2090,
        "location_status": "LOCATION_CURRENT",
        "assigned_event_id": "evt_01",
    },
    {
        "officer_id": "FO-002",
        "name": "Officer Priya Patel",
        "role": "FIELD_OFFICER",
        "status": "AVAILABLE",
        "current_latitude": 28.6145,
        "current_longitude": 77.2098,
        "location_status": "LOCATION_CURRENT",
        "assigned_event_id": "evt_01",
    },
    {
        "officer_id": "FO-003",
        "name": "Rapid Response Unit Alpha",
        "role": "RESPONSE_TEAM",
        "status": "AVAILABLE",
        "current_latitude": None,
        "current_longitude": None,
        "location_status": "LOCATION_UNKNOWN",
        "assigned_event_id": "evt_01",
    },
    {
        "officer_id": "FO-004",
        "name": "Officer Vikram Singh",
        "role": "FIELD_OFFICER",
        "status": "OFFLINE",
        "current_latitude": None,
        "current_longitude": None,
        "location_status": "LOCATION_UNKNOWN",
        "assigned_event_id": "evt_01",
    },
]


def seed_default_officers_if_empty(db: Session) -> List[ResponseOfficer]:
    """Ensure baseline test fixture officers exist in DB for operator selection."""
    for off_data in DEFAULT_OFFICERS:
        existing = db.query(ResponseOfficer).filter(ResponseOfficer.officer_id == off_data["officer_id"]).first()
        if not existing:
            officer = ResponseOfficer(
                officer_id=off_data["officer_id"],
                name=off_data["name"],
                role=off_data["role"],
                status=off_data["status"],
                current_latitude=off_data["current_latitude"],
                current_longitude=off_data["current_longitude"],
                location_status=off_data["location_status"],
                location_timestamp=datetime.now(timezone.utc) if off_data["current_latitude"] else None,
                assigned_event_id=off_data["assigned_event_id"],
            )
            db.add(officer)
    try:
        db.commit()
    except Exception:
        db.rollback()
    return db.query(ResponseOfficer).all()


def list_response_officers(db: Session, event_id: str = "evt_01") -> List[ResponseOfficer]:
    """Retrieve all response officers registered for an event."""
    seed_default_officers_if_empty(db)
    return db.query(ResponseOfficer).filter(
        ResponseOfficer.assigned_event_id == event_id
    ).order_by(ResponseOfficer.officer_id.asc()).all()


def get_incident_dispatches(db: Session, incident_id: str) -> List[DispatchAssignment]:
    """Retrieve all dispatch assignments for a specific incident."""
    return db.query(DispatchAssignment).filter(
        DispatchAssignment.incident_id == incident_id
    ).order_by(DispatchAssignment.created_at.desc()).all()


def get_dispatch_by_id(db: Session, dispatch_id: str) -> Optional[DispatchAssignment]:
    """Retrieve a single dispatch assignment with transitions."""
    return db.query(DispatchAssignment).filter(
        DispatchAssignment.dispatch_id == dispatch_id
    ).first()


def create_dispatch_assignment(
    db: Session,
    incident_id: str,
    officer_id: str,
    eta_minutes: int = 5,
    reason: str = "Operator requested field team deployment",
    assigned_by: str = "SYSTEM_OPERATOR",
) -> DispatchAssignment:
    """
    Creates a new dispatch assignment linking an active incident to a field officer.
    - Rejects dispatch creation for terminal incidents (RESOLVED, FALSE_POSITIVE).
    - Idempotence: Returns existing active dispatch if (incident_id, officer_id) already active.
    - Emits real-time WS DISPATCH_UPDATE event.
    """
    incident = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found."
        )

    if incident.status in ("RESOLVED", "FALSE_POSITIVE"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create dispatch for terminal incident '{incident_id}' (status: {incident.status})."
        )

    officer = db.query(ResponseOfficer).filter(ResponseOfficer.officer_id == officer_id).first()
    if not officer:
        # Fallback check by name or user_id
        seed_default_officers_if_empty(db)
        officer = db.query(ResponseOfficer).filter(ResponseOfficer.officer_id == officer_id).first()
        if not officer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Response officer '{officer_id}' not found."
            )

    # Idempotence & Duplicate active dispatch check
    existing = db.query(DispatchAssignment).filter(
        DispatchAssignment.incident_id == incident_id,
        DispatchAssignment.officer_id == officer_id,
        DispatchAssignment.status.notin_(["COMPLETED", "CANCELLED"])
    ).first()

    if existing:
        logger.info("Duplicate active dispatch check: returning existing dispatch %s", existing.dispatch_id)
        return existing

    dispatch_id = f"DSP-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc)

    assignment = DispatchAssignment(
        dispatch_id=dispatch_id,
        incident_id=incident.incident_id,
        event_id=incident.event_id,
        officer_id=officer.officer_id,
        status="ASSIGNED",
        assigned_by=assigned_by,
        assigned_at=now,
        eta_minutes=eta_minutes,
        dispatch_reason=reason,
    )
    db.add(assignment)

    # Update officer status to ASSIGNED
    officer.status = "ASSIGNED"
    officer.updated_at = now

    # Append immutable transition audit record
    transition_id = f"TRN-DSP-{uuid.uuid4().hex[:8].upper()}"
    trans = DispatchTransition(
        transition_id=transition_id,
        dispatch_id=dispatch_id,
        previous_status="UNASSIGNED",
        new_status="ASSIGNED",
        timestamp=now,
        actor_type="OPERATOR",
        actor_id=assigned_by,
        reason=reason,
        metadata_json={
            "incident_id": incident_id,
            "officer_id": officer_id,
            "eta_minutes": eta_minutes,
        }
    )
    db.add(trans)

    db.commit()
    db.refresh(assignment)

    # Broadcast WebSocket realtime dispatch event failure-safely
    try:
        from app.services.realtime_stream import realtime_stream_manager
        payload = {
            "dispatch_id": assignment.dispatch_id,
            "incident_id": assignment.incident_id,
            "event_id": assignment.event_id,
            "officer_id": assignment.officer_id,
            "status": assignment.status,
            "timestamp": now.isoformat(),
            "actor": assigned_by,
            "reason": reason,
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(realtime_stream_manager.broadcast_dispatch_update(payload))
        except RuntimeError:
            asyncio.run(realtime_stream_manager.broadcast_dispatch_update(payload))
    except Exception as err:
        logger.warning("Failed to broadcast WS dispatch update: %s", err)

    return assignment


def transition_dispatch_status(
    db: Session,
    dispatch_id: str,
    new_status: str,
    reason: Optional[str] = None,
    actor_type: str = "OPERATOR",
    actor_id: Optional[str] = None,
) -> DispatchAssignment:
    """
    Executes a lifecycle status transition on a dispatch assignment.
    Validates state machine rules, updates timestamps, updates officer availability,
    and appends an immutable audit log entry.
    Does NOT auto-resolve parent incident!
    """
    assignment = db.query(DispatchAssignment).filter(DispatchAssignment.dispatch_id == dispatch_id).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispatch assignment '{dispatch_id}' not found."
        )

    current_status = assignment.status
    allowed = VALID_DISPATCH_TRANSITIONS.get(current_status, set())

    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid dispatch status transition from '{current_status}' to '{new_status}'. Allowed transitions: {sorted(list(allowed))}"
        )

    now = datetime.now(timezone.utc)
    assignment.status = new_status
    assignment.updated_at = now

    if reason:
        assignment.notes = reason

    # Update state-specific timestamps & officer status
    officer = db.query(ResponseOfficer).filter(ResponseOfficer.officer_id == assignment.officer_id).first()

    if new_status == "ACKNOWLEDGED":
        assignment.acknowledged_at = now
        if officer:
            officer.status = "ASSIGNED"
    elif new_status == "EN_ROUTE":
        assignment.en_route_at = now
        if officer:
            officer.status = "BUSY"
    elif new_status == "ON_SCENE":
        assignment.on_scene_at = now
        if officer:
            officer.status = "BUSY"
    elif new_status == "RESPONDING":
        assignment.responding_at = now
        if officer:
            officer.status = "BUSY"
    elif new_status == "COMPLETED":
        assignment.completed_at = now
        if officer:
            officer.status = "AVAILABLE"
    elif new_status == "CANCELLED":
        assignment.cancelled_at = now
        if officer:
            officer.status = "AVAILABLE"

    # Append immutable transition audit log
    transition_id = f"TRN-DSP-{uuid.uuid4().hex[:8].upper()}"
    trans = DispatchTransition(
        transition_id=transition_id,
        dispatch_id=dispatch_id,
        previous_status=current_status,
        new_status=new_status,
        timestamp=now,
        actor_type=actor_type,
        actor_id=actor_id,
        reason=reason,
    )
    db.add(trans)

    db.commit()
    db.refresh(assignment)

    # Broadcast WebSocket realtime dispatch update event
    try:
        from app.services.realtime_stream import realtime_stream_manager
        payload = {
            "dispatch_id": assignment.dispatch_id,
            "incident_id": assignment.incident_id,
            "event_id": assignment.event_id,
            "officer_id": assignment.officer_id,
            "status": assignment.status,
            "timestamp": now.isoformat(),
            "actor": actor_id or actor_type,
            "reason": reason,
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(realtime_stream_manager.broadcast_dispatch_update(payload))
        except RuntimeError:
            asyncio.run(realtime_stream_manager.broadcast_dispatch_update(payload))
    except Exception as err:
        logger.warning("Failed to broadcast WS dispatch update: %s", err)

    return assignment
