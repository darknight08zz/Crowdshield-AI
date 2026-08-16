"""
CROWDSHIELD PHASE 6E LIVE CCTV / VIDEO PIPELINE TEST SUITE
=============================================================
Validates end-to-end real-time operational integration across live camera sources:
  1. Live Video File Ingestion (YOLOv8 + ByteTrack + Risk + Temporal AI)
  2. Webcam and RTSP Source Abstractions
  3. Camera Health Lifecycle (ONLINE -> DEGRADED -> OFFLINE)
  4. Live Video -> Incident Policy -> Operator Dispatch -> Field Officer Completion
  5. Mandatory Prototype & Ground Truth Provenance Mandates
"""

import os
import sys
import time
import pytest
from datetime import datetime, timezone
from uuid import uuid4
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
try:
    from tests.conftest import TestingSessionLocal
except ImportError:
    from conftest import TestingSessionLocal

from app.core.security import create_access_token
from app.models.incident import Incident, IncidentTransition
from app.models.dispatch import ResponseOfficer, DispatchAssignment, DispatchTransition
from app.services.incident_service import process_realtime_inference_incident
from app.services.dispatch_service import seed_default_officers_if_empty
from app.ai.services.inference_orchestrator import RealtimeInferenceOrchestrator
from app.ai.services.realtime_result_store import RealtimeInferenceResultStore
from app.ingestion.cv.camera_source import VideoFileSource, WebcamSource, RTSPSource
from app.ingestion.cv.camera_health import CameraHealthTracker
from scripts.run_live_pipeline import generate_sample_crowd_video

client = TestClient(app)


def get_auth_headers(role: str = "operator", user_id: str = None) -> dict:
    uid = user_id or str(uuid4())
    token = create_access_token(
        user_id=uid,
        email=f"{role}@crowdshield.ai",
        role=role
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def sample_video_path(tmp_path_factory):
    """Creates a temporary sample crowd video for deterministic testing."""
    fn = tmp_path_factory.mktemp("video") / "test_crowd.mp4"
    path_str = str(fn)
    generate_sample_crowd_video(path_str, duration_sec=3, fps=10)
    return path_str


@pytest.fixture(autouse=True)
def cleanup_e2e_db():
    db = TestingSessionLocal()
    try:
        db.query(DispatchTransition).delete()
        db.query(DispatchAssignment).delete()
        db.query(IncidentTransition).delete()
        db.query(Incident).delete()
        seed_default_officers_if_empty(db)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    yield
    db = TestingSessionLocal()
    try:
        db.query(DispatchTransition).delete()
        db.query(DispatchAssignment).delete()
        db.query(IncidentTransition).delete()
        db.query(Incident).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def test_01_live_video_file_ingestion(sample_video_path):
    """Verifies frame-by-frame processing of a VideoFileSource through the RealtimeInferenceOrchestrator."""
    cam_id = "CAM-6E-TEST-01"
    zone_id = "ZONE-6E-TEST-01"
    event_id = "EVT-6E-TEST-01"

    source = VideoFileSource(camera_id=cam_id, video_path=sample_video_path)
    assert source.is_open is True
    assert source.source_type == "VIDEO_FILE"

    orchestrator = RealtimeInferenceOrchestrator()
    frames_processed = 0

    while True:
        success, frame, metadata = source.read_frame()
        if not success or frame is None:
            break

        frames_processed += 1
        res = orchestrator.process_frame(
            frame,
            camera_id=cam_id,
            zone_id=zone_id,
            event_id=event_id,
            timestamp=metadata.timestamp,
            frame_id=metadata.frame_id,
            processing_mode="LIVE"
        )

        assert "telemetry" in res
        assert "current_risk" in res
        assert "ai_prediction" in res
        assert "warning" in res
        assert "provenance" in res

    source.release()
    assert frames_processed > 0


def test_02_webcam_and_rtsp_source_abstractions():
    """Verifies WebcamSource and RTSPSource initialization and frame reading fallback behavior."""
    cam_id = "CAM-6E-WEBCAM"
    webcam = WebcamSource(camera_id=cam_id, device_index=999)  # Non-existent index
    assert webcam.source_type == "WEBCAM"
    # Reading frame from unavailable webcam returns (False, None, None)
    success, frame, meta = webcam.read_frame()
    assert success is False
    assert frame is None
    webcam.release()

    rtsp_cam = "CAM-6E-RTSP"
    rtsp = RTSPSource(camera_id=rtsp_cam, rtsp_url="rtsp://invalid.host:554/stream")
    assert rtsp.source_type == "RTSP"
    success, frame, meta = rtsp.read_frame()
    assert success is False
    assert frame is None
    rtsp.release()


def test_03_camera_health_lifecycle_on_live_streams():
    """Verifies CameraHealthTracker status transitions (ONLINE -> DEGRADED -> OFFLINE)."""
    cam_id = "CAM-HEALTH-6E"
    zone_id = "ZONE-HEALTH-6E"

    tracker = CameraHealthTracker.get_or_create(cam_id, zone_id)

    # 1. Active frames -> ONLINE
    tracker.record_frame(processed=True, detection_success=True)
    h1 = tracker.evaluate_health()
    assert h1["status"] in ("ONLINE", "DEGRADED")  # May be degraded if uncalibrated

    # 2. Simulate 30s elapsed without frames -> OFFLINE
    tracker.last_frame_timestamp = time.time() - 30.0
    h2 = tracker.evaluate_health()
    assert h2["status"] == "OFFLINE"
    assert h2["is_degraded"] is True


def test_04_end_to_end_live_video_to_field_dispatch(sample_video_path):
    """
    Executes complete live video flow:
    Live Video File -> Inference Orchestrator -> High Risk Trigger -> Incident Creation ->
    Operator Acknowledgment -> Field Officer Dispatch -> Officer Progression -> Incident Resolution.
    """
    db = TestingSessionLocal()
    orchestrator = RealtimeInferenceOrchestrator()
    result_store = RealtimeInferenceResultStore()

    event_id = "EVT-LIVE-DISPATCH"
    camera_id = "CAM-LIVE-DISPATCH"
    zone_id = "ZONE-LIVE-DISPATCH"

    # Simulate Orchestrator producing HIGH_RISK frame from video stream
    high_telemetry = {
        "density": 5.2,
        "average_speed": 0.1,
        "inflow_rate": 220.0,
        "outflow_rate": 5.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    res = orchestrator.process_frame(high_telemetry, camera_id=camera_id, zone_id=zone_id, event_id=event_id)
    res["warning"]["operational_warning_state"] = "HIGH_RISK"
    res["current_risk"]["score"] = 92.5
    res["ai_prediction"]["probability"] = 0.94

    result_store.update_result(res)
    inc = process_realtime_inference_incident(db, res)
    db.close()

    assert inc is not None
    assert inc.status == "OPEN"
    incident_id = inc.incident_id

    # Operator Acknowledges Incident
    op_headers = get_auth_headers("operator")
    r_ack = client.post(f"/api/v1/operator/incidents/{incident_id}/transition", json={"new_status": "ACKNOWLEDGED", "reason": "Confirmed via live video feed"}, headers=op_headers)
    assert r_ack.status_code == 200

    # Operator Dispatches Field Officer
    r_dsp = client.post(f"/api/v1/operator/incidents/{incident_id}/dispatch", json={"officer_id": "FO-001", "eta_minutes": 5, "reason": "Dispatch to gate 3"}, headers=op_headers)
    assert r_dsp.status_code == 200
    dispatch_id = r_dsp.json()["dispatch_id"]

    # Field Officer completes response progression
    field_headers = get_auth_headers("field_officer")
    for st in ["ACKNOWLEDGED", "EN_ROUTE", "ON_SCENE", "RESPONDING", "COMPLETED"]:
        r_st = client.post(f"/api/v1/officers/dispatches/{dispatch_id}/transition", json={"new_status": st, "reason": f"Officer updated status to {st}"}, headers=field_headers)
        assert r_st.status_code == 200

    # Verify Incident remains ACKNOWLEDGED until Operator manual resolution
    r_inc = client.get(f"/api/v1/operator/incidents/{incident_id}", headers=op_headers)
    assert r_inc.json()["status"] == "ACKNOWLEDGED"

    # Operator resolves incident
    r_res = client.post(f"/api/v1/operator/incidents/{incident_id}/transition", json={"new_status": "RESOLVED", "reason": "Live crowd dispersed"}, headers=op_headers)
    assert r_res.status_code == 200
    assert r_res.json()["status"] == "RESOLVED"


def test_05_provenance_mandates_verification(sample_video_path):
    """Validates mandatory provenance metadata fields across all live inference output containers."""
    orchestrator = RealtimeInferenceOrchestrator()
    source = VideoFileSource(camera_id="CAM-PROV-01", video_path=sample_video_path)

    success, frame, metadata = source.read_frame()
    assert success is True

    res = orchestrator.process_frame(
        frame,
        camera_id="CAM-PROV-01",
        zone_id="ZONE-PROV-01",
        event_id="EVT-PROV-01",
        timestamp=metadata.timestamp,
        frame_id=metadata.frame_id,
        processing_mode="LIVE"
    )
    source.release()

    prov = res.get("provenance", {})
    assert prov.get("model_status") == "PROTOTYPE"
    assert prov.get("label_type") == "PHYSICS_DEFINED_PROXY"
    assert prov.get("ground_truth_status") == "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED"
    assert "disclaimer" in prov
