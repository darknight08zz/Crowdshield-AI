from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.security import require_role, UserPayload
from app.models import OfficerAssignment
from app.schemas.assignment import OfficerAssignmentResponse, OfficerAssignmentStatusUpdate
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
        assignments = db.query(OfficerAssignment).filter(
            OfficerAssignment.officer_id == UUID(current_user.id)
        ).order_by(OfficerAssignment.created_at.desc()).all()
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
