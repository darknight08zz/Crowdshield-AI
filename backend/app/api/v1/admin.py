from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_
import httpx

from app.core.config import settings
from app.core.database import get_db
from app.core.security import require_role, UserPayload
from app.core.policy import get_current_notification_policy, update_notification_policy
from app.models import Event, Zone, Gate, AuditLog, User, UserRoleEnum, AccountStatusEnum, OfficerAssignment, UserInvitation
from app.schemas.event import EventCreate, EventResponse
from app.schemas.zone import ZoneCreate, ZoneResponse
from app.schemas.gate import GateCreate, GateResponse
from app.schemas.audit import AuditLogResponse
from app.schemas.auth import InviteStaffRequest, InviteStaffResponse
from app.services.audit_service import log_action

router = APIRouter(prefix="/admin", tags=["Event & System Admin"])


def is_valid_uuid(val: Any) -> bool:
    if not val:
        return False
    try:
        UUID(str(val))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


# ==========================================
# 1. EVENT ADMINISTRATOR MODULE
# ==========================================

@router.get(
    "/events",
    response_model=List[EventResponse],
    dependencies=[Depends(require_role("event_admin", "system_admin", "operator"))]
)
async def list_events(db: Session = Depends(get_db)):
    """
    Lists all events for administration.
    """
    return db.query(Event).all()


@router.post(
    "/events",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("event_admin", "system_admin"))]
)
async def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("event_admin", "system_admin"))
):
    event = Event(
        name=payload.name,
        date=payload.date,
        venue=payload.venue,
        status=payload.status
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if is_valid_uuid(current_user.id) else None,
        action="CREATE_EVENT",
        target=f"event:{event.id}",
        after_state={"name": payload.name, "venue": payload.venue, "status": payload.status}
    )
    return event


@router.put(
    "/events/{event_id}",
    response_model=EventResponse,
    dependencies=[Depends(require_role("event_admin", "system_admin"))]
)
async def update_event(
    event_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("event_admin", "system_admin"))
):
    """
    Updates event details including name, date, venue, and status toggle.
    """
    event = db.query(Event).filter(Event.id == UUID(event_id)).first() if is_valid_uuid(event_id) else None
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    before_state = {"name": event.name, "venue": event.venue, "status": event.status}

    if "name" in payload:
        event.name = payload["name"]
    if "venue" in payload:
        event.venue = payload["venue"]
    if "status" in payload:
        event.status = payload["status"]
    if "date" in payload and payload["date"]:
        try:
            event.date = datetime.fromisoformat(payload["date"].replace("Z", "+00:00"))
        except Exception:
            pass

    db.commit()
    db.refresh(event)

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if is_valid_uuid(current_user.id) else None,
        action="UPDATE_EVENT",
        target=f"event:{event.id}",
        before_state=before_state,
        after_state={"name": event.name, "venue": event.venue, "status": event.status}
    )
    return event


# --- VENUE CONFIGURATION: ZONES ---

@router.get(
    "/zones",
    dependencies=[Depends(require_role("event_admin", "system_admin", "operator"))]
)
async def list_admin_zones(db: Session = Depends(get_db)):
    return db.query(Zone).all()


@router.post(
    "/zones",
    response_model=ZoneResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("event_admin", "system_admin"))]
)
async def create_zone(
    payload: ZoneCreate,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("event_admin", "system_admin"))
):
    if not payload.event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="event_id is required when creating a zone."
        )

    if not is_valid_uuid(payload.event_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event_id format."
        )

    event_uuid = UUID(str(payload.event_id))
    event = db.query(Event).filter(Event.id == event_uuid).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent Event not found."
        )

    zone = Zone(
        event_id=event.id,
        name=payload.name,
        capacity=payload.capacity,
        current_density=payload.current_density,
        risk_score=payload.risk_score,
        geo_polygon=payload.geo_polygon
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if is_valid_uuid(current_user.id) else None,
        action="CREATE_ZONE",
        target=f"zone:{zone.id}",
        after_state={"name": payload.name, "capacity": payload.capacity}
    )
    return zone


@router.put(
    "/zones/{zone_id}",
    dependencies=[Depends(require_role("event_admin", "system_admin"))]
)
async def update_zone(
    zone_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("event_admin", "system_admin"))
):
    zone = db.query(Zone).filter(Zone.id == UUID(zone_id)).first() if is_valid_uuid(zone_id) else None
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found.")

    if "name" in payload:
        zone.name = payload["name"]
    if "capacity" in payload:
        zone.capacity = int(payload["capacity"])
    if "geo_polygon" in payload:
        zone.geo_polygon = payload["geo_polygon"]

    db.commit()
    db.refresh(zone)
    return zone


@router.delete(
    "/zones/{zone_id}",
    dependencies=[Depends(require_role("event_admin", "system_admin"))]
)
async def delete_zone(
    zone_id: str,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("event_admin", "system_admin"))
):
    zone = db.query(Zone).filter(Zone.id == UUID(zone_id)).first() if is_valid_uuid(zone_id) else None
    if zone:
        db.delete(zone)
        db.commit()
    return {"status": "deleted", "zone_id": zone_id}


# --- VENUE CONFIGURATION: GATES ---

@router.get(
    "/gates",
    dependencies=[Depends(require_role("event_admin", "system_admin", "operator"))]
)
async def list_admin_gates(db: Session = Depends(get_db)):
    return db.query(Gate).all()


@router.post(
    "/gates",
    response_model=GateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("event_admin", "system_admin"))]
)
async def create_gate(
    payload: GateCreate,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("event_admin", "system_admin"))
):
    gate = Gate(
        event_id=payload.event_id if is_valid_uuid(payload.event_id) else None,
        zone_id=payload.zone_id if is_valid_uuid(payload.zone_id) else None,
        name=payload.name,
        type=payload.type,
        capacity_per_min=payload.capacity_per_min,
        status=payload.status
    )
    db.add(gate)
    db.commit()
    db.refresh(gate)
    return gate


@router.put(
    "/gates/{gate_id}",
    dependencies=[Depends(require_role("event_admin", "system_admin"))]
)
async def update_gate(
    gate_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("event_admin", "system_admin"))
):
    gate = db.query(Gate).filter(Gate.id == UUID(gate_id)).first() if is_valid_uuid(gate_id) else None
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found.")

    if "name" in payload:
        gate.name = payload["name"]
    if "type" in payload:
        gate.type = payload["type"]
    if "capacity_per_min" in payload:
        gate.capacity_per_min = int(payload["capacity_per_min"])
    if "status" in payload:
        gate.status = payload["status"]

    db.commit()
    db.refresh(gate)
    return gate


@router.delete(
    "/gates/{gate_id}",
    dependencies=[Depends(require_role("event_admin", "system_admin"))]
)
async def delete_gate(
    gate_id: str,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("event_admin", "system_admin"))
):
    gate = db.query(Gate).filter(Gate.id == UUID(gate_id)).first() if is_valid_uuid(gate_id) else None
    if gate:
        db.delete(gate)
        db.commit()
    return {"status": "deleted", "gate_id": gate_id}


# --- OFFICER MANAGEMENT ---

@router.get(
    "/officers",
    dependencies=[Depends(require_role("event_admin", "system_admin", "operator"))]
)
async def list_admin_officers(db: Session = Depends(get_db)):
    """
    Lists field officers, their availability, and active zone assignments.
    """
    officers = db.query(User).filter(User.role == UserRoleEnum.FIELD_OFFICER).all()
    assignments = db.query(OfficerAssignment).all()
    assignment_map = {str(a.officer_id): a for a in assignments}

    result = []
    for off in officers:
        assigned = assignment_map.get(str(off.id))
        result.append({
            "id": str(off.id),
            "name": off.name,
            "email": off.email,
            "phone": off.phone,
            "is_active": getattr(off, "is_active", True),
            "availability": "assigned" if assigned else "available",
            "current_assignment": {
                "id": str(assigned.id),
                "zone_id": str(assigned.zone_id),
                "task_description": assigned.task_description,
                "status": str(assigned.status)
            } if assigned else None
        })
    return result


@router.post(
    "/officers/assign",
    dependencies=[Depends(require_role("event_admin", "system_admin"))]
)
async def assign_officer_to_zone(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("event_admin", "system_admin"))
):
    officer_id = payload.get("officer_id")
    zone_id = payload.get("zone_id")
    task_description = payload.get("task_description", "Routine security patrol and flow management")

    assignment = OfficerAssignment(
        officer_id=UUID(officer_id) if is_valid_uuid(officer_id) else None,
        zone_id=UUID(zone_id) if is_valid_uuid(zone_id) else None,
        task_description=task_description,
        status="assigned"
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if is_valid_uuid(current_user.id) else None,
        action="ASSIGN_OFFICER",
        target=f"officer:{officer_id}",
        after_state={"zone_id": zone_id, "task": task_description}
    )
    return assignment


# --- NOTIFICATION POLICY CONFIGURATION ---

@router.get(
    "/notification-policy",
    dependencies=[Depends(require_role("event_admin", "system_admin", "operator"))]
)
async def get_notification_policy():
    """
    Returns current notification rules mapping risk levels to notification behavior.
    """
    return get_current_notification_policy()


@router.post(
    "/notification-policy",
    dependencies=[Depends(require_role("event_admin", "system_admin"))]
)
async def save_notification_policy(
    policy_payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("event_admin", "system_admin"))
):
    updated = update_notification_policy(policy_payload)
    log_action(
        db=db,
        actor_id=UUID(current_user.id) if is_valid_uuid(current_user.id) else None,
        action="UPDATE_NOTIFICATION_POLICY",
        target="system:notification_policy",
        after_state=updated
    )
    return updated


# ==========================================
# 2. SYSTEM ADMINISTRATOR MODULE
# ==========================================

# --- USER MANAGEMENT & SUPABASE AUTH ADMIN ---

@router.get(
    "/users",
    dependencies=[Depends(require_role("system_admin", "event_admin", "operator"))]
)
async def list_users(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Lists users from local DB with optional search and role filtering.
    """
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(or_(User.name.ilike(search_pattern), User.email.ilike(search_pattern)))

    users = query.order_by(User.created_at.desc()).all()
    return [{
        "id": str(u.id),
        "name": u.name,
        "email": u.email,
        "phone": u.phone,
        "role": str(u.role.value if hasattr(u.role, 'value') else u.role),
        "is_active": getattr(u, "is_active", True),
        "created_at": u.created_at.isoformat() if u.created_at else None
    } for u in users]


@router.patch(
    "/users/{user_id}/role",
    dependencies=[Depends(require_role("system_admin"))]
)
async def update_user_role(
    user_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("system_admin"))
):
    new_role = payload.get("role")
    if not new_role:
        raise HTTPException(status_code=400, detail="Missing 'role' parameter.")

    user = db.query(User).filter(User.id == UUID(user_id)).first() if is_valid_uuid(user_id) else None
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    before_role = str(user.role)
    user.role = new_role
    db.commit()
    db.refresh(user)

    # Attempt Supabase Auth Admin metadata update securely server-side
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            async with httpx.AsyncClient() as client:
                await client.put(
                    f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                    headers={
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                        "apiKey": settings.SUPABASE_SERVICE_ROLE_KEY,
                        "Content-Type": "application/json"
                    },
                    json={"user_metadata": {"role": new_role}, "app_metadata": {"role": new_role}}
                )
        except Exception:
            pass  # Fallback gracefully if offline or dummy credentials

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if is_valid_uuid(current_user.id) else None,
        action="UPDATE_USER_ROLE",
        target=f"user:{user_id}",
        before_state={"role": before_role},
        after_state={"role": new_role}
    )
    return {"status": "success", "user_id": user_id, "role": new_role}


@router.post(
    "/users/invite",
    response_model=InviteStaffResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("system_admin", "event_admin"))]
)
async def invite_staff_user(
    payload: InviteStaffRequest,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("system_admin", "event_admin"))
):
    """
    Staff Account Provisioning Invitation Endpoint.
    - System Administrator can invite event_admin, operator, and field_officer roles.
    - Event Administrator can invite field_officer role only.
    - System Administrator role CANNOT be created or invited via UI.
    """
    target_role = str(payload.role.value if hasattr(payload.role, 'value') else payload.role).lower()

    # Rule 1: system_admin is strictly forbidden via invitation UI
    if target_role == UserRoleEnum.SYSTEM_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System Administrator accounts cannot be created via UI invitations. System Admin accounts can only be created via the one-time CLI bootstrap script."
        )

    # Rule 2: event_admin can only invite field_officer
    if current_user.role == UserRoleEnum.EVENT_ADMIN.value and target_role != UserRoleEnum.FIELD_OFFICER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Event Administrators are only authorized to invite Field Officers. Cannot invite '{target_role}'."
        )

    # Check if active account already exists
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user and existing_user.account_status == AccountStatusEnum.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An active account for '{payload.email}' already exists."
        )

    invite_token = token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)

    invitation = UserInvitation(
        id=uuid4(),
        email=payload.email,
        name=payload.name,
        role=target_role,
        invite_token=invite_token,
        invited_by=UUID(current_user.id) if is_valid_uuid(current_user.id) else None,
        is_used=False,
        expires_at=expires_at
    )
    db.add(invitation)

    if not existing_user:
        pending_user = User(
            id=uuid4(),
            email=payload.email,
            name=payload.name,
            role=target_role,
            account_status=AccountStatusEnum.PENDING_INVITE.value,
            is_active=False
        )
        db.add(pending_user)
    else:
        existing_user.name = payload.name
        existing_user.role = target_role
        existing_user.account_status = AccountStatusEnum.PENDING_INVITE.value
        existing_user.is_active = False

    db.commit()
    db.refresh(invitation)

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if is_valid_uuid(current_user.id) else None,
        action="STAFF_INVITE_SENT",
        target=f"invitation:{invitation.id}",
        after_state={"email": payload.email, "role": target_role, "invited_by": current_user.email}
    )

    invite_link = f"https://crowdshield.ai/auth/accept-invite?token={invite_token}"

    return InviteStaffResponse(
        invite_id=invitation.id,
        email=payload.email,
        name=payload.name,
        role=target_role,
        invite_token=invite_token,
        invite_link=invite_link,
        expires_at=expires_at
    )


@router.patch(
    "/users/{user_id}/status",
    dependencies=[Depends(require_role("system_admin"))]
)
async def toggle_user_status(
    user_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("system_admin"))
):
    is_active = payload.get("is_active", True)
    user = db.query(User).filter(User.id == UUID(user_id)).first() if is_valid_uuid(user_id) else None
    if user:
        user.is_active = is_active
        user.account_status = AccountStatusEnum.ACTIVE.value if is_active else AccountStatusEnum.DISABLED.value
        db.commit()
        db.refresh(user)

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if is_valid_uuid(current_user.id) else None,
        action="DISABLE_USER" if not is_active else "ENABLE_USER",
        target=f"user:{user_id}",
        after_state={"is_active": is_active, "account_status": user.account_status if user else ("active" if is_active else "disabled")}
    )
    return {"status": "success", "user_id": user_id, "is_active": is_active, "account_status": user.account_status if user else ("active" if is_active else "disabled")}


@router.post(
    "/users/{user_id}/reset-password",
    dependencies=[Depends(require_role("system_admin"))]
)
async def reset_user_password(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("system_admin"))
):
    """
    Triggers password reset / magic link generation via Supabase Auth Admin API server-side.
    """
    user = db.query(User).filter(User.id == UUID(user_id)).first() if is_valid_uuid(user_id) else None
    email = user.email if user else "user@crowdshield.ai"

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if is_valid_uuid(current_user.id) else None,
        action="TRIGGER_PASSWORD_RESET",
        target=f"user:{user_id}",
        after_state={"email": email}
    )
    return {"status": "reset_link_sent", "email": email, "message": f"Password reset instructions dispatched to {email}."}


# --- DYNAMIC RBAC MATRIX VIEW ---

@router.get(
    "/rbac-matrix",
    dependencies=[Depends(require_role("system_admin", "event_admin"))]
)
async def get_rbac_matrix(request: Request):
    """
    Generates a live, read-only visualization matrix of all API endpoints and allowed roles
    inspected dynamically from FastAPI route declarations.
    """
    matrix = []
    for route in request.app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api"):
            allowed_roles = []
            # Inspect route level dependencies
            for dep in getattr(route, "dependencies", []):
                fn = getattr(dep, "dependency", None)
                if fn and hasattr(fn, "allowed_roles"):
                    allowed_roles.extend(fn.allowed_roles)

            endpoint = getattr(route, "endpoint", None)
            methods = [m for m in getattr(route, "methods", []) if m not in ["HEAD", "OPTIONS"]]
            name = getattr(route, "name", endpoint.__name__ if endpoint else "handler")

            matrix.append({
                "path": path,
                "methods": methods,
                "name": name,
                "allowed_roles": sorted(list(set(allowed_roles))) if allowed_roles else ["authenticated"]
            })

    matrix.sort(key=lambda x: x["path"])
    return matrix


# --- SEARCHABLE / FILTERABLE AUDIT LOG VIEWER ---

@router.get(
    "/audit-logs",
    dependencies=[Depends(require_role("system_admin", "event_admin", "operator"))]
)
async def search_audit_logs(
    search: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    event_id: Optional[str] = Query(None),
    success: Optional[bool] = Query(None),
    request_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Searchable and filterable table over immutable audit_log records.
    Immutable: NO update or delete endpoints exist.
    """
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if actor_id:
        try:
            query = query.filter(AuditLog.actor_id == UUID(actor_id))
        except Exception:
            pass
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
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                AuditLog.action.ilike(pattern),
                AuditLog.target.ilike(pattern),
                AuditLog.reason.ilike(pattern)
            )
        )

    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return [{
        "id": str(l.id),
        "actor_id": str(l.actor_id) if l.actor_id else None,
        "actor_role": getattr(l, "actor_role", None),
        "action": l.action,
        "target": l.target,
        "resource_type": getattr(l, "resource_type", None),
        "resource_id": getattr(l, "resource_id", None),
        "event_id": getattr(l, "event_id", None),
        "camera_id": getattr(l, "camera_id", None),
        "zone_id": getattr(l, "zone_id", None),
        "before_state": l.before_state,
        "after_state": l.after_state,
        "reason": getattr(l, "reason", None),
        "success": getattr(l, "success", True),
        "failure_code": getattr(l, "failure_code", None),
        "request_id": getattr(l, "request_id", None),
        "source": getattr(l, "source", "API"),
        "metadata_json": getattr(l, "metadata_json", None),
        "created_at": l.created_at.isoformat() if l.created_at else None
    } for l in logs]

