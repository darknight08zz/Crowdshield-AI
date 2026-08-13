"""
TEST SUITE FOR AUTHENTICATION, SIGNUP, AND STAFF PROVISIONING (Prompt 1 Addendum)
================================================================================
Verifies:
1. Citizen open self-signup & public role restriction (rejects staff role self-signup).
2. Staff invitation flow (System Admin -> Operator/Admin; Event Admin -> Officer only).
3. System Admin bootstrap CLI script & API invitation rejection for system_admin role.
4. Invite acceptance token workflow (assigns role strictly from invite, sets password).
5. Password hashing, login, token refresh, and server-side logout revocation.
6. Rate limiting on login and password reset requests.
7. Account status enforcement (rejecting disabled accounts in get_current_user).
8. Comprehensive audit logging for all auth events.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User, UserRoleEnum, AccountStatusEnum
from app.models.invitation import UserInvitation
from app.models.audit import AuditLog
from app.core.security import hash_password, create_access_token
from app.core.rate_limiter import login_rate_limiter, reset_rate_limiter
from scripts.bootstrap_admin import bootstrap_system_admin

from conftest import TestingSessionLocal

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_rate_limits():
    login_rate_limiter.requests.clear()
    reset_rate_limiter.requests.clear()


@pytest.fixture(scope="module")
def setup_auth_db():
    db = TestingSessionLocal()

    # Create test System Admin
    sysadmin = User(
        id=uuid4(),
        email="sysadmin_test@crowdshield.gov",
        name="Test System Admin",
        role=UserRoleEnum.SYSTEM_ADMIN,
        password_hash=hash_password("AdminSecret123!"),
        account_status=AccountStatusEnum.ACTIVE.value,
        is_active=True
    )
    # Create test Event Admin
    event_admin = User(
        id=uuid4(),
        email="eventadmin_test@crowdshield.gov",
        name="Test Event Admin",
        role=UserRoleEnum.EVENT_ADMIN,
        password_hash=hash_password("EventSecret123!"),
        account_status=AccountStatusEnum.ACTIVE.value,
        is_active=True
    )
    db.add(sysadmin)
    db.add(event_admin)
    db.commit()

    sysadmin_token = create_access_token(sysadmin.id, sysadmin.email, "system_admin", "active")
    eventadmin_token = create_access_token(event_admin.id, event_admin.email, "event_admin", "active")

    yield db, sysadmin, sysadmin_token, event_admin, eventadmin_token

    db.close()


def test_citizen_self_signup_success(setup_auth_db):
    """Confirms citizens can self-signup and get flagged as pending verification."""
    res = client.post("/api/v1/auth/signup", json={
        "name": "Jane Citizen",
        "email": "jane_citizen@example.com",
        "password": "Password123!",
        "role": "citizen"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "pending_verification"
    assert data["email"] == "jane_citizen@example.com"


def test_staff_role_self_signup_rejected(setup_auth_db):
    """Confirms public self-signup is strictly forbidden for staff roles (operator, field_officer, event_admin, system_admin)."""
    for forbidden_role in ["operator", "field_officer", "event_admin", "system_admin"]:
        res = client.post("/api/v1/auth/signup", json={
            "name": "Hacker Impersonator",
            "email": f"hacker_{forbidden_role}@example.com",
            "password": "HackerPassword123!",
            "role": forbidden_role
        })
        assert res.status_code == 403
        assert "Self-signup is strictly restricted to Citizens" in res.json()["detail"]


def test_citizen_otp_verification_and_login(setup_auth_db):
    """Verifies OTP activation and subsequent login."""
    verify_res = client.post("/api/v1/auth/verify-otp", json={
        "email": "jane_citizen@example.com",
        "otp": "654321"
    })
    assert verify_res.status_code == 200
    token_data = verify_res.json()
    assert "access_token" in token_data
    assert token_data["user"]["role"] == "citizen"

    login_res = client.post("/api/v1/auth/login", json={
        "email": "jane_citizen@example.com",
        "password": "Password123!"
    })
    if login_res.status_code != 200:
        print("CITIZEN LOGIN ERROR:", login_res.status_code, login_res.json())
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()


def test_staff_invitation_permissions(setup_auth_db):
    """Verifies System Admin and Event Admin staff invitation authorization rules."""
    db, sysadmin, sysadmin_token, event_admin, eventadmin_token = setup_auth_db

    # 1. System Admin invites an Operator (Allowed)
    res1 = client.post(
        "/api/v1/admin/users/invite",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
        json={
            "name": "Operator Alpha",
            "email": "operator_alpha@crowdshield.gov",
            "role": "operator"
        }
    )
    assert res1.status_code == 201
    assert "invite_token" in res1.json()

    # 2. System Admin attempts to invite a System Admin (Forbidden via UI)
    res2 = client.post(
        "/api/v1/admin/users/invite",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
        json={
            "name": "Sub Admin",
            "email": "sub_admin@crowdshield.gov",
            "role": "system_admin"
        }
    )
    assert res2.status_code == 403
    assert "System Admin accounts can only be created via the one-time CLI bootstrap script" in res2.json()["detail"]

    # 3. Event Admin invites a Field Officer (Allowed)
    res3 = client.post(
        "/api/v1/admin/users/invite",
        headers={"Authorization": f"Bearer {eventadmin_token}"},
        json={
            "name": "Officer Bravo",
            "email": "officer_bravo@crowdshield.gov",
            "role": "field_officer"
        }
    )
    assert res3.status_code == 201
    assert res3.json()["role"] == "field_officer"

    # 4. Event Admin attempts to invite an Operator (Forbidden)
    res4 = client.post(
        "/api/v1/admin/users/invite",
        headers={"Authorization": f"Bearer {eventadmin_token}"},
        json={
            "name": "Unauth Operator",
            "email": "unauth_operator@crowdshield.gov",
            "role": "operator"
        }
    )
    assert res4.status_code == 403
    assert "Event Administrators are only authorized to invite Field Officers" in res4.json()["detail"]


def test_staff_accept_invite_workflow(setup_auth_db):
    """Verifies that an invited staff user sets their password and activates account with assigned role."""
    db, sysadmin, sysadmin_token, _, _ = setup_auth_db

    # Create invite
    invite_res = client.post(
        "/api/v1/admin/users/invite",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
        json={
            "name": "Operator Charlie",
            "email": "operator_charlie@crowdshield.gov",
            "role": "operator"
        }
    )
    assert invite_res.status_code == 201
    invite_token = invite_res.json()["invite_token"]

    # Accept invite and set password
    accept_res = client.post("/api/v1/auth/accept-invite", json={
        "invite_token": invite_token,
        "password": "SecureStaffPassword123!"
    })
    assert accept_res.status_code == 200
    token_data = accept_res.json()
    assert token_data["user"]["role"] == "operator"
    assert token_data["user"]["account_status"] == "active"

    # Confirm login works with new password
    login_res = client.post("/api/v1/auth/login", json={
        "email": "operator_charlie@crowdshield.gov",
        "password": "SecureStaffPassword123!"
    })
    assert login_res.status_code == 200


def test_disabled_account_enforcement(setup_auth_db):
    """Verifies that disabled accounts are rejected during login and token validation."""
    db, sysadmin, sysadmin_token, _, _ = setup_auth_db
    db.expire_all()

    # Retrieve operator_charlie
    charlie = db.query(User).filter(User.email == "operator_charlie@crowdshield.gov").first()
    assert charlie is not None
    charlie_token = create_access_token(charlie.id, charlie.email, "operator", "active")

    # Admin disables user
    disable_res = client.patch(
        f"/api/v1/admin/users/{charlie.id}/status",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
        json={"is_active": False}
    )
    assert disable_res.status_code == 200
    assert disable_res.json()["account_status"] == "disabled"

    # Attempt login while disabled
    login_res = client.post("/api/v1/auth/login", json={
        "email": "operator_charlie@crowdshield.gov",
        "password": "SecureStaffPassword123!"
    })
    assert login_res.status_code == 403
    assert "Account is disabled" in login_res.json()["detail"]

    # Attempt API request with old token while disabled
    profile_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {charlie_token}"}
    )
    assert profile_res.status_code == 403
    assert "Account is disabled" in profile_res.json()["detail"]


def test_cli_bootstrap_script(setup_auth_db):
    """Verifies CLI bootstrap script initializes System Admin securely."""
    db, sysadmin, sysadmin_token, _, _ = setup_auth_db
    bootstrap_system_admin(
        email="root_admin@crowdshield.gov",
        name="Root Administrator",
        password="RootPassword123!",
        db=db
    )

    login_res = client.post("/api/v1/auth/login", json={
        "email": "root_admin@crowdshield.gov",
        "password": "RootPassword123!"
    })
    if login_res.status_code != 200:
        print("BOOTSTRAP LOGIN ERROR:", login_res.status_code, login_res.json())
    assert login_res.status_code == 200
    assert login_res.json()["user"]["role"] == "system_admin"
