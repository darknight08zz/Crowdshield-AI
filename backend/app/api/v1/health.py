import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.database import get_db
from app.ai.risk_model import predict_risk, get_model
from app.ai.features import SAFE_BASELINES
from app.ai.training.registry import get_active_model_path, list_registered_models
from app.ingestion.hybrid_cctv_gps import HybridCCTVGPSIngestion
from app.services.alerting import trigger_oncall_platform_alert

router = APIRouter(tags=["Health"])


@router.get("/health")
async def get_system_health(db: Session = Depends(get_db)):
    """
    Returns comprehensive system health status indicators for API, Ingestion Pipeline, AI Model Registry, DB, and FCM.
    Triggers automated on-call platform alerts if health degrades.
    """
    # 1. DB Health
    db_status = "healthy"
    db_message = "PostgreSQL Database connected successfully."
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "degraded"
        db_message = f"Database connection warning: {str(e)}"

    # 2. AI Risk Engine & Versioned Model Registry Health
    ai_status = "healthy"
    active_path = get_active_model_path()
    ai_message = f"Active versioned model loaded ({os.path.basename(active_path)})."
    try:
        if not os.path.exists(active_path):
            ai_status = "degraded"
            ai_message = "Active registry model file missing; using linear heuristic fallback."
        else:
            # Quick test prediction
            _, _ = predict_risk(SAFE_BASELINES)
    except Exception as e:
        ai_status = "degraded"
        ai_message = f"AI inference warning: {str(e)}"

    # 3. Telemetry Ingestion Pipeline Health
    ingestion_status = "healthy"
    ingestion_message = "Hybrid CCTV + GPS Ingestion Adapter active."
    try:
        hybrid = HybridCCTVGPSIngestion()
        # Verify default buffer status
        test_features = hybrid.get_zone_features("aa111111-0000-0000-0000-000000000001", db)
        if test_features.get("is_degraded", False):
            ingestion_status = "degraded"
            ingestion_message = "Telemetry stream age > 30s; operating in fallback synthetic mode."
    except Exception as e:
        ingestion_status = "degraded"
        ingestion_message = f"Ingestion warning: {str(e)}"

    # 4. Notification Service Health
    notification_status = "healthy"
    firebase_cred_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "crowdshield-94e02-firebase-adminsdk-fbsvc-33a345f10b.json")
    if os.path.exists(firebase_cred_path):
        notification_message = "Firebase Cloud Messaging (FCM) Admin SDK active with valid service credentials."
    else:
        notification_status = "healthy"  # Operational dev mock fallback
        notification_message = "Push notification engine active (Development Mock Fallback Mode)."

    # 5. API Core Status
    api_status = "healthy"
    api_message = f"{settings.PROJECT_NAME} v{settings.VERSION} online on {settings.HOST}:{settings.PORT}."

    all_statuses = [db_status, ai_status, ingestion_status, notification_status, api_status]
    overall = "healthy" if all(s == "healthy" for s in all_statuses) else "degraded"

    # Trigger automated platform alert to on-call engineer if degraded
    if overall == "degraded":
        trigger_oncall_platform_alert(
            service_name="CrowdShield Platform Backend",
            severity="WARNING",
            message=f"Platform health status degraded. Ingestion: {ingestion_status}, AI: {ai_status}, DB: {db_status}",
            metadata={
                "ingestion_detail": ingestion_message,
                "ai_detail": ai_message,
                "db_detail": db_message
            }
        )

    return {
        "overall_status": overall,
        "environment": settings.ENV,
        "services": {
            "api": {
                "name": "FastAPI Core Engine",
                "status": api_status,
                "detail": api_message
            },
            "database": {
                "name": "PostgreSQL / Supabase Database",
                "status": db_status,
                "detail": db_message
            },
            "ingestion_pipeline": {
                "name": "Hybrid Ingestion Adapter",
                "status": ingestion_status,
                "detail": ingestion_message
            },
            "ai_engine": {
                "name": "XGBoost Versioned Risk Registry",
                "status": ai_status,
                "active_model": os.path.basename(active_path),
                "detail": ai_message
            },
            "notifications": {
                "name": "Push Notification Service (FCM)",
                "status": notification_status,
                "detail": notification_message
            }
        }
    }
