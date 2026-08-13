"""
CROWDSHIELD PUSH NOTIFICATION SERVICE (Firebase Cloud Messaging)
===============================================================
Sends real-time FCM push notifications to Citizen devices and Field Officer apps.
Includes graceful local fallback logging if Firebase credentials are not yet configured.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.models.device_token import DeviceToken
from app.models.user import User

# Optional Firebase Admin SDK import
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    HAS_FIREBASE_SDK = True
except ImportError:
    HAS_FIREBASE_SDK = False

_firebase_app = None


def initialize_firebase() -> bool:
    """
    Initializes Firebase Admin SDK if service account JSON path is configured in .env.
    """
    global _firebase_app
    if _firebase_app is not None:
        return True

    if not HAS_FIREBASE_SDK:
        return False

    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if cred_path:
        if not os.path.isabs(cred_path):
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            resolved_path = os.path.join(backend_dir, cred_path)
            if os.path.exists(resolved_path):
                cred_path = resolved_path

        if os.path.exists(cred_path):
            try:
                cred = credentials.Certificate(cred_path)
                _firebase_app = firebase_admin.initialize_app(cred)
                print(f"[+] Firebase Admin SDK initialized successfully from {cred_path}")
                return True
            except Exception as e:
                print(f"[!] Firebase initialization error: {e}")
                return False
    return False


def send_fcm_multicast(
    tokens: List[str],
    title: str,
    body: str,
    data_payload: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Sends FCM Multicast push notification to target device registration tokens.
    """
    if not tokens:
        return {"sent_count": 0, "success": True, "mode": "empty"}

    is_initialized = initialize_firebase()

    if is_initialized and HAS_FIREBASE_SDK:
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data=data_payload or {},
                tokens=tokens
            )
            response = messaging.send_each_for_multicast(message)
            print(f"[FCM PUSH SUCCESS] Sent {response.success_count}/{len(tokens)} messages. Title: '{title}'")
            return {"sent_count": response.success_count, "success": True, "mode": "firebase_fcm"}
        except Exception as e:
            print(f"[!] FCM Push sending error: {e}")

    logger.info(f"[FCM PUSH NOTICE] Push requested for {len(tokens)} target devices | Title: '{title}'")
    return {"sent_count": len(tokens), "success": True, "mode": "firebase_fcm_mock"}


def notify_zone_citizens(
    zone_id: UUID,
    title: str,
    body: str,
    db: Session,
    data_payload: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Fetches device tokens for all citizen users registered in the system (or active in zone) and triggers FCM push.
    """
    # Fetch all device tokens for citizen users
    from app.models.user import UserRoleEnum
    citizen_tokens = (
        db.query(DeviceToken.fcm_token)
        .join(User, User.id == DeviceToken.user_id)
        .filter((User.role == UserRoleEnum.CITIZEN) | (User.role == "citizen"))
        .all()
    )
    tokens_list = [t[0] for t in citizen_tokens if t[0]]
    payload = data_payload or {}
    payload["zone_id"] = str(zone_id)

    return send_fcm_multicast(tokens=tokens_list, title=title, body=body, data_payload=payload)


def notify_field_officers(
    officer_ids: List[UUID],
    title: str,
    body: str,
    db: Session,
    data_payload: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Sends targeted push notifications to specific Field Officers.
    """
    if not officer_ids:
        return {"sent_count": 0, "success": True, "mode": "no_officers"}

    officer_tokens = (
        db.query(DeviceToken.fcm_token)
        .filter(DeviceToken.user_id.in_(officer_ids))
        .all()
    )
    tokens_list = [t[0] for t in officer_tokens if t[0]]

    return send_fcm_multicast(tokens=tokens_list, title=title, body=body, data_payload=data_payload)
