from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user, UserPayload
from app.models.device_token import DeviceToken
from app.schemas.device import DeviceTokenRegister, DeviceTokenResponse

router = APIRouter(prefix="/devices", tags=["Device Push Registration"])


@router.post(
    "/register",
    response_model=DeviceTokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)]
)
async def register_device_token(
    payload: DeviceTokenRegister,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(get_current_user)
):
    """
    Registers or updates a device FCM registration push token for the logged-in user.
    Allowed roles: ALL authenticated roles (citizen, field_officer, operator, etc.)
    """
    if not current_user.id:
        raise HTTPException(status_code=401, detail="Invalid user authentication payload.")

    user_id = UUID(current_user.id)

    # Check if token already exists
    existing = db.query(DeviceToken).filter(DeviceToken.fcm_token == payload.fcm_token).first()
    if existing:
        existing.user_id = user_id
        existing.platform = payload.platform
        db.commit()
        db.refresh(existing)
        return existing

    # Create new device token registration
    device_token = DeviceToken(
        user_id=user_id,
        fcm_token=payload.fcm_token,
        platform=payload.platform
    )
    db.add(device_token)
    db.commit()
    db.refresh(device_token)

    return device_token
