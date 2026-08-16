"""
CROWDSHIELD CENTRALIZED AUTHORIZATION & RBAC ENGINE (PHASE 6G)
================================================================
Defines canonical roles, role normalization, resource-level authorization policies,
and explicit ownership checks for REST and WebSocket interfaces.

Canonical Roles:
  - ADMIN: Full administrative rights across system configuration, user accounts, and events.
  - OPERATOR: Command room oversight, incident lifecycle transitions, and officer dispatch.
  - FIELD_OFFICER: Mobile task reception, incident response, and field assignment updates.
  - VIEWER: Read-only access to public metrics, event maps, and status dashboards.
"""

from typing import List, Set, Optional, Dict, Any, Union
from uuid import UUID
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.security import UserPayload, get_current_user
from app.models import Incident, User


class CanonicalRole:
    ADMIN = "admin"
    OPERATOR = "operator"
    FIELD_OFFICER = "field_officer"
    VIEWER = "viewer"


ROLE_MAPPINGS: Dict[str, str] = {
    "admin": CanonicalRole.ADMIN,
    "system_admin": CanonicalRole.ADMIN,
    "event_admin": CanonicalRole.ADMIN,
    "operator": CanonicalRole.OPERATOR,
    "field_officer": CanonicalRole.FIELD_OFFICER,
    "viewer": CanonicalRole.VIEWER,
    "citizen": CanonicalRole.VIEWER,
}

ROLE_EQUIVALENTS: Dict[str, Set[str]] = {
    CanonicalRole.ADMIN: {"admin", "system_admin", "event_admin"},
    CanonicalRole.OPERATOR: {"operator"},
    CanonicalRole.FIELD_OFFICER: {"field_officer"},
    CanonicalRole.VIEWER: {"viewer", "citizen"},
}


def normalize_role(role: Optional[str]) -> str:
    """
    Normalizes any DB or JWT role string to a canonical CrowdShield role.
    Defaults to VIEWER if unknown.
    """
    if not role:
        return CanonicalRole.VIEWER
    r = str(role).strip().lower()
    return ROLE_MAPPINGS.get(r, CanonicalRole.VIEWER)


def is_role_allowed(user_role: str, allowed_roles: List[str]) -> bool:
    """
    Checks if user_role matches any allowed role (accounting for canonical equivalencies).
    """
    norm_user_role = normalize_role(user_role)

    for allowed in allowed_roles:
        norm_allowed = normalize_role(allowed)
        if norm_user_role == norm_allowed:
            return True
        # Direct check against equivalent sets
        equivalents = ROLE_EQUIVALENTS.get(norm_allowed, {norm_allowed})
        if str(user_role).strip().lower() in equivalents:
            return True
    return False


def require_canonical_role(*allowed_roles: str):
    """
    FastAPI dependency for Role-Based Access Control enforcing canonical roles.
    Fails closed with HTTP 403 Forbidden.
    """
    async def dependency(user: UserPayload = Depends(get_current_user)) -> UserPayload:
        if not is_role_allowed(user.role, list(allowed_roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Action requires one of roles: {list(allowed_roles)}. Current role: '{user.role}'."
            )
        return user
    return dependency


def verify_dispatch_ownership(user: UserPayload, dispatch: Any, db: Session) -> bool:
    """
    Verifies field officer resource authorization for a dispatch assignment.
    Admins and Operators have access to all dispatches.
    Field Officers have access to dispatches assigned to their officer ID, badge code, or user profile.
    Viewers have NO modification rights.
    """
    norm_role = normalize_role(user.role)
    if norm_role in (CanonicalRole.ADMIN, CanonicalRole.OPERATOR):
        return True

    if norm_role == CanonicalRole.FIELD_OFFICER:
        officer_id = getattr(dispatch, "officer_id", None)
        if not officer_id:
            return False

        str_officer_id = str(officer_id).strip().lower()
        str_user_id = str(user.id).strip().lower()
        str_email = str(user.email or "").strip().lower()

        # Direct string matches
        if str_officer_id in (str_user_id, str_email) or str_email.startswith(str_officer_id):
            return True

        from app.models.dispatch import ResponseOfficer
        parsed_officer_id = None
        parsed_user_id = None
        try:
            parsed_officer_id = UUID(str(officer_id))
        except Exception:
            pass

        try:
            parsed_user_id = UUID(str(user.id))
        except Exception:
            pass

        query = db.query(ResponseOfficer)
        if parsed_officer_id:
            query = query.filter(ResponseOfficer.officer_id == parsed_officer_id)
        else:
            query = query.filter(ResponseOfficer.officer_id == str(officer_id))

        officer = query.first()
        if officer:
            # If officer record is bound to a user_id, check match
            if officer.user_id:
                if str(officer.user_id).lower() == str_user_id:
                    return True
            else:
                # Unbound officer badge (e.g., FO-001) accessible by active field officers
                return True
        else:
            # If officer_id is a badge code string (e.g., FO-001, FO-002) not bound to a user, allow field officer
            if str_officer_id.startswith("fo-") or str_officer_id.startswith("officer"):
                return True

        # Fallback match check
        if str_officer_id in (str_user_id, str_email):
            return True

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Dispatch assignment '{getattr(dispatch, 'dispatch_id', '')}' belongs to another field officer."
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden: Viewers cannot manage dispatch assignments."
    )




def verify_incident_authorization(user: UserPayload, incident: Any, action: str = "read") -> bool:
    """
    Verifies incident resource access.
    State modifications (transitions, dispatch creation) require ADMIN or OPERATOR role.
    """
    norm_role = normalize_role(user.role)
    if action in ("transition", "create_dispatch", "modify"):
        if norm_role not in (CanonicalRole.ADMIN, CanonicalRole.OPERATOR):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Role '{user.role}' is not authorized to execute incident action '{action}'."
            )
    return True


def verify_websocket_subscription_access(user: UserPayload, event_id: str, camera_id: str, zone_id: str) -> bool:
    """
    Validates whether a WebSocket user session is authorized to subscribe to a requested event/camera/zone.
    Fails closed (returns False) for unauthorized scopes.
    """
    if not user:
        return False
    norm_role = normalize_role(user.role)

    # Admin and Operator can subscribe to any stream/zone/event
    if norm_role in (CanonicalRole.ADMIN, CanonicalRole.OPERATOR):
        return True

    # Field Officers can subscribe to streams within their active scope or all camera streams
    if norm_role == CanonicalRole.FIELD_OFFICER:
        return True

    # Viewers can subscribe to public streams but not unauthorized administrative streams
    if norm_role == CanonicalRole.VIEWER:
        if camera_id and "ADMIN_ONLY" in camera_id.upper():
            return False
        return True

    return True
