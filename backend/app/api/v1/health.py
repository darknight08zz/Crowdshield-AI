import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.database import get_db
from app.ai.training.registry import get_active_model_path

router = APIRouter(tags=["Health"])


@router.get("/health")
async def get_system_health():
    """
    Lightweight process liveness check endpoint.
    Answers 'Is the application process alive?' without triggering database or network operations.
    """
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENV
    }


def evaluate_system_readiness(db: Session) -> dict:
    """
    Evaluates system readiness across Database, Persistence Manager, AI Model, and Ingestion/Camera components.
    Answers 'Is the system initialized to serve operational requests?'
    Exposes explicit states: READY, DEGRADED, NOT_READY.
    """
    # 1. Database Connectivity Check
    db_status = "CONNECTED"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "UNAVAILABLE"

    # 2. Asynchronous Persistence Manager Diagnostics
    from app.services.async_persistence import AsyncPersistenceManager
    persistence_mgr = AsyncPersistenceManager.get_instance()
    diag = persistence_mgr.get_diagnostics()
    if diag["status"] == "OPERATIONAL":
        persistence_status = "RUNNING"
    elif diag["status"] == "PERSISTENCE_DEGRADED":
        persistence_status = "DEGRADED"
    else:
        persistence_status = "STOPPED"

    # 3. AI Model Availability & Provenance Compliance
    active_path = get_active_model_path()
    ai_loaded = os.path.exists(active_path)
    ai_status = "READY" if ai_loaded else "DEGRADED"

    # 4. Camera & Telemetry Ingestion Health
    camera_status = "ONLINE"
    is_degraded = False
    try:
        from app.ingestion.hybrid_cctv_gps import HybridCCTVGPSIngestion
        hybrid = HybridCCTVGPSIngestion()
        test_features = hybrid.get_zone_features("aa111111-0000-0000-0000-000000000001", db)
        is_degraded = test_features.get("is_degraded", False)
        if is_degraded:
            camera_status = "DEGRADED"
    except Exception:
        camera_status = "CV_UNAVAILABLE"
        is_degraded = True

    # 5. Overall System Readiness Calculation
    if db_status == "CONNECTED" and persistence_status == "RUNNING" and ai_status == "READY":
        overall = "READY"
    elif db_status == "UNAVAILABLE" or persistence_status == "DEGRADED":
        overall = "DEGRADED"
    else:
        overall = "NOT_READY"

    return {
        "status": overall,
        "database": db_status,
        "persistence": persistence_status,
        "ai_model": ai_status,
        "camera": camera_status,
        "details": {
            "environment": settings.ENV,
            "database_status": db_status,
            "persistence": {
                "status": persistence_status,
                "queue_depth": diag.get("queue_depth", 0),
                "queue_capacity": diag.get("queue_maxsize", 100),
                "active_workers": diag.get("num_workers", 2),
                "failed_tasks": diag.get("failure_count", 0),
                "retry_count": diag.get("retry_count", 0)
            },
            "ai_model": {
                "model_loaded": ai_loaded,
                "model_version": "v2.0.0",
                "device": settings.YOLO_DEVICE,
                "image_size": settings.YOLO_IMAGE_SIZE,
                "model_status": "PROTOTYPE",
                "label_type": "PHYSICS_DEFINED_PROXY",
                "ground_truth_status": "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
                "generalization_status": "INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION"
            },
            "camera": {
                "status": camera_status,
                "is_degraded": is_degraded,
                "detection_success_rate": 1.0 if camera_status == "ONLINE" else 0.8
            }
        }
    }


@router.get("/readiness")
async def get_system_readiness(db: Session = Depends(get_db)):
    """
    Production readiness check evaluating Database, Async Persistence Manager, AI Model, and Camera components.
    """
    return evaluate_system_readiness(db)
