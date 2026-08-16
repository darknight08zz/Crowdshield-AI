from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.security import require_role, UserPayload
from app.models import OfficerAssignment, Incident
from app.schemas.assignment import OfficerAssignmentResponse, OfficerAssignmentStatusUpdate
from app.schemas.dispatch import (
    DispatchCanonicalResponse,
    DispatchTransitionRequest as DispatchTransReq,
    FieldOfficerAssignmentContextResponse,
)
from app.services.dispatch_service import (
    get_dispatch_by_id,
    transition_dispatch_status,
)
from app.models.dispatch import DispatchAssignment, ResponseOfficer
from app.services.audit_service import log_action

router = APIRouter(prefix="/officers", tags=["Field Officers"])


@router.get(
    "/assignments",
    response_model=List[OfficerAssignmentResponse],
    dependencies=[Depends(require_role("field_officer", "operator", "system_admin"))]
)
async def get_assigned_tasks(
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("field_officer", "operator", "system_admin"))
):
    """
    Fetches dispatched tasks assigned to the requesting field officer.
    Allowed roles: field_officer, operator, system_admin
    """
    if current_user.role == "field_officer":
        try:
            val_uuid = UUID(current_user.id)
            assignments = db.query(OfficerAssignment).filter(
                OfficerAssignment.officer_id == val_uuid
            ).order_by(OfficerAssignment.created_at.desc()).all()
        except Exception:
            assignments = []
    else:
        # Operators and admins view all assignments
        assignments = db.query(OfficerAssignment).order_by(OfficerAssignment.created_at.desc()).all()
    
    return assignments


@router.patch(
    "/assignments/{assignment_id}/status",
    response_model=OfficerAssignmentResponse,
    dependencies=[Depends(require_role("field_officer", "operator", "system_admin"))]
)
async def update_assignment_status(
    assignment_id: UUID,
    payload: OfficerAssignmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("field_officer", "operator", "system_admin"))
):
    """
    Updates the status of a dispatched field officer task (e.g. acknowledged, in_progress, completed).
    Allowed roles: field_officer, operator, system_admin
    """
    assignment = db.query(OfficerAssignment).filter(OfficerAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Officer Assignment not found.")

    before_status = assignment.status
    assignment.status = payload.status
    db.commit()
    db.refresh(assignment)

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if current_user.id else None,
        action="UPDATE_OFFICER_ASSIGNMENT_STATUS",
        target=f"assignment:{assignment.id}",
        before_state={"status": str(before_status)},
        after_state={"status": str(payload.status)}
    )

    return assignment


# ============================================================================
# PHASE 6D.3 CANONICAL FIELD OFFICER DISPATCH ENDPOINTS
# ============================================================================

from app.core.authorization import verify_dispatch_ownership, normalize_role, CanonicalRole


@router.get(
    "/dispatches",
    response_model=List[DispatchCanonicalResponse],
    dependencies=[Depends(require_role("field_officer", "operator", "system_admin", "event_admin"))]
)
async def get_my_field_dispatches(
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("field_officer", "operator", "system_admin", "event_admin"))
):
    """
    Returns active dispatch assignments assigned to the authenticated field officer.
    Operators/Admins receive all dispatches.
    """
    query = db.query(DispatchAssignment)
    norm_role = normalize_role(current_user.role)

    if norm_role == CanonicalRole.FIELD_OFFICER:
        officer = db.query(ResponseOfficer).filter(
            (ResponseOfficer.user_id == current_user.id) |
            (ResponseOfficer.officer_id == current_user.id) |
            (ResponseOfficer.name.ilike(f"%{current_user.email or ''}%"))
        ).first()

        if officer:
            query = query.filter(DispatchAssignment.officer_id == officer.officer_id)
        else:
            query = query.filter(
                (DispatchAssignment.officer_id == current_user.id) |
                (DispatchAssignment.officer_id == (current_user.email or ""))
            )

    return query.order_by(DispatchAssignment.created_at.desc()).all()


@router.get(
    "/dispatches/{dispatch_id}",
    response_model=FieldOfficerAssignmentContextResponse,
    dependencies=[Depends(require_role("field_officer", "operator", "system_admin", "event_admin"))]
)
async def get_field_dispatch_context(
    dispatch_id: str,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("field_officer", "operator", "system_admin", "event_admin"))
):
    """
    Returns full field officer dispatch assignment context, including parent incident telemetry,
    physics risk, AI probability, and model prototype disclaimer box.
    Enforces resource authorization: field officer can only view their own dispatch.
    """
    dispatch = get_dispatch_by_id(db, dispatch_id=dispatch_id)
    if not dispatch:
        raise HTTPException(status_code=404, detail=f"Dispatch assignment '{dispatch_id}' not found.")

    verify_dispatch_ownership(current_user, dispatch, db)

    incident = db.query(Incident).filter(Incident.incident_id == dispatch.incident_id).first()
    
    return FieldOfficerAssignmentContextResponse(
        dispatch=dispatch,
        incident_id=dispatch.incident_id,
        zone_id=incident.zone_id if incident else "ZONE-UNKNOWN",
        event_id=dispatch.event_id,
        camera_id=incident.camera_id if incident else None,
        warning_state=incident.latest_warning_state or incident.warning_state_at_creation if incident else "EARLY_WARNING",
        physics_risk=incident.latest_physics_risk or incident.physics_risk_at_creation if incident else 75.0,
        ai_probability=incident.latest_ai_probability or incident.ai_probability_at_creation if incident else 0.85,
        model_version=incident.model_version if incident else "v2.0.0",
        label_type=incident.label_type if incident else "PHYSICS_DEFINED_PROXY",
        model_status=incident.model_status if incident else "PROTOTYPE",
        disclaimer=incident.disclaimer if incident else "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated."
    )


@router.post(
    "/dispatches/{dispatch_id}/transition",
    response_model=DispatchCanonicalResponse,
    dependencies=[Depends(require_role("field_officer", "operator", "system_admin", "event_admin"))]
)
async def transition_field_dispatch(
    dispatch_id: str,
    payload: DispatchTransReq,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("field_officer", "operator", "system_admin", "event_admin"))
):
    """
    Executes status transition on a dispatch assignment from the field officer's device.
    Enforces resource authorization: field officer can only transition their assigned dispatch.
    """
    dispatch = get_dispatch_by_id(db, dispatch_id=dispatch_id)
    if not dispatch:
        raise HTTPException(status_code=404, detail=f"Dispatch assignment '{dispatch_id}' not found.")

    verify_dispatch_ownership(current_user, dispatch, db)

    actor_id = current_user.email or current_user.id or "FIELD_OFFICER"
    return transition_dispatch_status(
        db=db,
        dispatch_id=dispatch_id,
        new_status=payload.new_status,
        reason=payload.reason,
        actor_type="FIELD_OFFICER",
        actor_id=actor_id,
    )

