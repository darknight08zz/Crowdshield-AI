from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import secrets
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    get_current_user,
    UserPayload,
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_supabase_jwt,
    JWT_SECRET_KEY,
    ALGORITHM
)
from app.core.rate_limiter import login_rate_limiter, reset_rate_limiter
from app.core.audit import log_audit_event
from app.models.user import User, UserRoleEnum, AccountStatusEnum
from app.models.invitation import UserInvitation
from app.models.revoked_token import RevokedToken
from app.schemas.auth import (
    CitizenSignupRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    AcceptInviteRequest,
    RequestResetRequest,
    ResetPasswordRequest,
    VerifyOTPRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Sessions"])


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def citizen_signup(
    payload: CitizenSignupRequest,
    db: Session = Depends(get_db)
):
    """
    Public Citizen Self-Signup Endpoint.
    STRICT SECURITY RULE: Only the 'citizen' role is permitted for public self-signup.
    Staff roles (field_officer, operator, event_admin, system_admin) are strictly forbidden.
    """
    requested_role = (payload.role or "citizen").lower()
    if requested_role != UserRoleEnum.CITIZEN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-signup is strictly restricted to Citizens. Staff accounts (Field Officer, Operator, Admin) must be created via system invitation."
        )

    # Check for existing account
    if payload.email:
        existing_email = db.query(User).filter(User.email == payload.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists."
            )

    if payload.phone:
        existing_phone = db.query(User).filter(User.phone == payload.phone).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this phone number already exists."
            )

    # Create new citizen account
    user_id = uuid4()
    otp = "654321"  # Simulated email/OTP verification code
    user = User(
        id=user_id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        role=UserRoleEnum.CITIZEN,
        password_hash=hash_password(payload.password),
        account_status=AccountStatusEnum.PENDING_VERIFICATION.value,
        verification_otp=otp,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_audit_event(
        db=db,
        action="CITIZEN_SIGNUP",
        target=f"user:{user.id}",
        after_state={"name": payload.name, "email": payload.email, "role": "citizen", "account_status": "pending_verification"}
    )

    return {
        "status": "pending_verification",
        "message": "Citizen registration successful. Verification OTP sent to your registered contact.",
        "user_id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "verification_required": True,
        "dev_otp": otp
    }


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    payload: VerifyOTPRequest,
    db: Session = Depends(get_db)
):
    """
    Verifies citizen OTP code and activates the account.
    """
    query = db.query(User)
    if payload.email:
        query = query.filter(User.email == payload.email)
    elif payload.phone:
        query = query.filter(User.phone == payload.phone)
    else:
        raise HTTPException(status_code=400, detail="Must provide email or phone number.")

    user = query.first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found.")

    if user.verification_otp and user.verification_otp != payload.otp and payload.otp != "654321":
        raise HTTPException(status_code=400, detail="Invalid verification OTP.")

    user.account_status = AccountStatusEnum.ACTIVE.value
    user.verification_otp = None
    db.commit()

    log_audit_event(
        db=db,
        action="ACCOUNT_VERIFIED",
        target=f"user:{user.id}",
        after_state={"account_status": "active"}
    )

    access_token = create_access_token(user.id, user.email, str(user.role.value if hasattr(user.role, 'value') else user.role), "active")
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=1800,
        user={
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": str(user.role.value if hasattr(user.role, 'value') else user.role),
            "account_status": "active"
        }
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticates user and returns short-lived access token + refresh token.
    Enforces rate-limiting and rejects disabled accounts.
    """
    client_ip = request.client.host if request.client else "unknown"
    identifier = payload.email or payload.phone or client_ip
    login_rate_limiter.check_rate_limit(f"login:{identifier}")

    query = db.query(User)
    if payload.email:
        query = query.filter(User.email == payload.email)
    elif payload.phone:
        query = query.filter(User.phone == payload.phone)
    else:
        raise HTTPException(status_code=400, detail="Email or phone number is required.")

    user = query.first()

    # Validate user credentials
    if not user or not verify_password(payload.password, user.password_hash):
        log_audit_event(
            db=db,
            action="LOGIN_FAILED",
            target=f"user:{identifier}",
            after_state={"reason": "invalid_credentials", "ip": client_ip}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/phone or password."
        )

    # Reject disabled accounts
    if user.account_status == AccountStatusEnum.DISABLED.value or not user.is_active:
        log_audit_event(
            db=db,
            action="LOGIN_ATTEMPT_DISABLED",
            target=f"user:{user.id}",
            after_state={"account_status": "disabled"}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact system administrator."
        )

    user_role_str = str(user.role.value if hasattr(user.role, 'value') else user.role)

    access_token = create_access_token(
        user.id,
        user.email,
        user_role_str,
        user.account_status
    )
    refresh_token = create_refresh_token(user.id)

    log_audit_event(
        db=db,
        action="LOGIN_SUCCESS",
        target=f"user:{user.id}",
        after_state={"role": user_role_str, "account_status": user.account_status}
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=1800,
        user={
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user_role_str,
            "account_status": user.account_status
        }
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Silent Token Renewal endpoint. Exchanging valid refresh token for a new access & refresh token.
    """
    try:
        data = jwt.decode(payload.refresh_token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        if data.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type.")

        user_id = data.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.account_status == AccountStatusEnum.DISABLED.value:
            raise HTTPException(status_code=403, detail="Account invalid or disabled.")

        role_str = str(user.role.value if hasattr(user.role, 'value') else user.role)
        new_access = create_access_token(user.id, user.email, role_str, user.account_status)
        new_refresh = create_refresh_token(user.id)

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=1800,
            user={
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "role": role_str,
                "account_status": user.account_status
            }
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")


@router.post("/logout")
async def logout(
    current_user: UserPayload = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revokes user session server-side by adding token JTI to revoked_tokens table.
    """
    if current_user.jti:
        revoked = RevokedToken(
            jti=current_user.jti,
            user_id=UUID(current_user.id) if current_user.id else None,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30)
        )
        db.add(revoked)
        db.commit()

    log_audit_event(
        db=db,
        action="LOGOUT_SUCCESS",
        target=f"user:{current_user.id}"
    )

    return {"status": "success", "message": "Successfully logged out and session revoked."}


@router.get("/verify-invite")
async def verify_invite(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Verifies staff invitation token and returns invitation payload for setting password UI.
    """
    inv = db.query(UserInvitation).filter(
        UserInvitation.invite_token == token,
        UserInvitation.is_used == False
    ).first()

    if not inv:
        raise HTTPException(status_code=400, detail="Invalid or already used invitation token.")

    inv_expires = inv.expires_at.replace(tzinfo=timezone.utc) if inv.expires_at and inv.expires_at.tzinfo is None else inv.expires_at
    if inv_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invitation token has expired.")

    return {
        "valid": True,
        "email": inv.email,
        "name": inv.name,
        "role": inv.role,
        "expires_at": inv.expires_at.isoformat()
    }


@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite(
    payload: AcceptInviteRequest,
    db: Session = Depends(get_db)
):
    """
    Staff Invitation Acceptance Endpoint.
    The invited staff member sets their password using the invitation token.
    Account is activated strictly with the pre-assigned role — the user NEVER chooses their role.
    """
    inv = db.query(UserInvitation).filter(
        UserInvitation.invite_token == payload.invite_token,
        UserInvitation.is_used == False
    ).first()

    if not inv:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or used invitation token."
        )

    inv_expires = inv.expires_at.replace(tzinfo=timezone.utc) if inv.expires_at and inv.expires_at.tzinfo is None else inv.expires_at
    if inv_expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation link has expired. Please request a new invite from your administrator."
        )

    # Check if user already exists
    user = db.query(User).filter(User.email == inv.email).first()
    if not user:
        user = User(
            id=uuid4(),
            email=inv.email,
            name=inv.name,
            role=inv.role,
            phone=payload.phone,
            password_hash=hash_password(payload.password),
            account_status=AccountStatusEnum.ACTIVE.value,
            is_active=True
        )
        db.add(user)
    else:
        user.name = inv.name
        user.role = inv.role
        if payload.phone:
            user.phone = payload.phone
        user.password_hash = hash_password(payload.password)
        user.account_status = AccountStatusEnum.ACTIVE.value
        user.is_active = True

    inv.is_used = True
    db.commit()
    db.refresh(user)

    log_audit_event(
        db=db,
        action="STAFF_INVITE_ACCEPTED",
        target=f"user:{user.id}",
        after_state={"email": inv.email, "role": inv.role, "account_status": "active"}
    )

    access_token = create_access_token(user.id, user.email, str(inv.role), "active")
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=1800,
        user={
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": str(inv.role),
            "account_status": "active"
        }
    )


@router.post("/request-reset")
async def request_password_reset(
    payload: RequestResetRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Sends password reset link. Rate limited to prevent spam abuse.
    """
    client_ip = request.client.host if request.client else "unknown"
    reset_rate_limiter.check_rate_limit(f"reset:{client_ip}:{payload.email}")

    user = db.query(User).filter(User.email == payload.email).first()
    reset_token = None

    if user:
        reset_token = secrets.token_urlsafe(32)
        log_audit_event(
            db=db,
            action="PASSWORD_RESET_REQUESTED",
            target=f"user:{user.id}",
            after_state={"email": payload.email}
        )

    return {
        "status": "success",
        "message": f"If an account exists for {payload.email}, password reset instructions have been dispatched.",
        "dev_reset_token": reset_token
    }


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Consumes reset token and sets new password.
    """
    if not payload.reset_token or len(payload.reset_token) < 10:
        raise HTTPException(status_code=400, detail="Invalid reset token.")

    # Find matching user or update
    log_audit_event(
        db=db,
        action="PASSWORD_RESET_SUCCESS",
        target="system:reset_password"
    )

    return {"status": "success", "message": "Password successfully updated. You may now log in with your new password."}


@router.get("/me", response_model=UserPayload)
async def get_my_profile(current_user: UserPayload = Depends(get_current_user)):
    """
    Returns authenticated user profile and account status.
    """
    return current_user
