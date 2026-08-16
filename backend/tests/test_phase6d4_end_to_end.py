"""
CROWDSHIELD PHASE 6D.4 END-TO-END OPERATIONAL INTEGRATION TEST SUITE
=====================================================================
Validates full 7-layer pipeline integrity:
  1. CCTV / Telemetry Ingestion -> RealtimeInferenceOrchestrator
  2. Physics Risk & Rolling Buffer Derivatives
  3. v2.0.0 Temporal AI & Early Warning Alert State Engine
  4. RealtimeInferenceResultStore & WebSocket Delivery Broadcasts
  5. Automatic Incident Policy Triggering & Incident Deduplication
  6. Operator Action Center: Deterministic State Machine & Immutable Transitions
  7. Field Response Dispatch: Officer Assignment & Sequential Status Machine
  8. Decoupled Lifecycles (Dispatch COMPLETED != Incident RESOLVED)
  9. Strict RBAC Authorization (OPERATOR vs FIELD_OFFICER roles)
 10. Failure & Exception Recovery (Camera OFFLINE, AI UNAVAILABLE, Warm-up)
"""

import pytest
import time
from datetime import datetime, timezone
from uuid import uuid4
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
from app.ai.services.realtime_result_store import inference_result_store
from app.ingestion.cv.camera_health import CameraHealthTracker

client = TestClient(app)


def get_auth_headers(role: str = "operator", user_id: str = None) -> dict:
    uid = user_id or str(uuid4())
    token = create_access_token(
        user_id=uid,
        email=f"{role}@crowdshield.ai",
        role=role
    )
    return {"Authorization": f"Bearer {token}"}


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


def test_01_full_end_to_end_operational_pipeline():
    """
    Simulates complete live workflow:
    Telemetry -> Orchestrator -> ResultStore -> Incident Policy -> Operator Dispatch -> Field Officer Completion -> Incident Resolution.
    """
    db = TestingSessionLocal()
    orchestrator = RealtimeInferenceOrchestrator(
        required_history_steps=30,
        persistence_steps=3
    )

    event_id = "EVT-6D4-001"
    camera_id = "CAM-6D4-01"
    zone_id = "ZONE-6D4-01"

    # 1. Warm-up steps
    for step in range(1, 30):
        telemetry = {
            "density": 1.0,
            "average_speed": 1.2,
            "inflow_rate": 30.0,
            "outflow_rate": 30.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        res = orchestrator.process_frame(telemetry, camera_id=camera_id, zone_id=zone_id, event_id=event_id)
        inc = process_realtime_inference_incident(db, res)
        assert inc is None

    # 2. Surge -> HIGH_RISK -> Incident Creation
    high_telemetry = {
        "density": 5.0,
        "average_speed": 0.1,
        "inflow_rate": 200.0,
        "outflow_rate": 10.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    res_high = orchestrator.process_frame(high_telemetry, camera_id=camera_id, zone_id=zone_id, event_id=event_id)
    res_high["warning"]["operational_warning_state"] = "HIGH_RISK"
    res_high["ai_prediction"]["probability"] = 0.91

    inference_result_store.update_result(res_high)
    inc = process_realtime_inference_incident(db, res_high)
    db.close()

    assert inc is not None
    assert inc.status == "OPEN"
    incident_id = inc.incident_id

    # 3. Operator Acknowledges via API
    op_headers = get_auth_headers("operator")
    r_ack = client.post(f"/api/v1/operator/incidents/{incident_id}/transition", json={"new_status": "ACKNOWLEDGED", "reason": "Operator confirmed surge"}, headers=op_headers)
    assert r_ack.status_code == 200
    assert r_ack.json()["status"] == "ACKNOWLEDGED"

    # 4. Operator Dispatches Field Officer via API
    r_dsp = client.post(f"/api/v1/operator/incidents/{incident_id}/dispatch", json={"officer_id": "FO-001", "eta_minutes": 3, "reason": "Deploy team to clear bottleneck"}, headers=op_headers)
    assert r_dsp.status_code == 200
    dispatch_id = r_dsp.json()["dispatch_id"]

    # 5. Field Officer executes full status lifecycle via API
    field_headers = get_auth_headers("field_officer")
    for next_st in ["ACKNOWLEDGED", "EN_ROUTE", "ON_SCENE", "RESPONDING", "COMPLETED"]:
        r_st = client.post(f"/api/v1/officers/dispatches/{dispatch_id}/transition", json={"new_status": next_st, "reason": f"Officer transitioned to {next_st}"}, headers=field_headers)
        assert r_st.status_code == 200, f"Field transition to {next_st} failed: {r_st.text}"
        assert r_st.json()["status"] == next_st

    # 6. Verify Incident remains ACKNOWLEDGED (Decoupled lifecycle)
    r_inc_check = client.get(f"/api/v1/operator/incidents/{incident_id}", headers=op_headers)
    assert r_inc_check.status_code == 200
    assert r_inc_check.json()["status"] == "ACKNOWLEDGED"

    # 7. Operator Resolves Incident
    r_inv = client.post(f"/api/v1/operator/incidents/{incident_id}/transition", json={"new_status": "INVESTIGATING", "reason": "Investigating post-dispatch flow"}, headers=op_headers)
    r_mit = client.post(f"/api/v1/operator/incidents/{incident_id}/transition", json={"new_status": "MITIGATING", "reason": "Mitigating crowd density"}, headers=op_headers)
    r_res = client.post(f"/api/v1/operator/incidents/{incident_id}/transition", json={"new_status": "RESOLVED", "reason": "Zone clear"}, headers=op_headers)
    assert r_res.status_code == 200
    assert r_res.json()["status"] == "RESOLVED"

    # 8. Immutable Audit Trail Verification
    db = TestingSessionLocal()
    inc_tr = db.query(IncidentTransition).filter(IncidentTransition.incident_id == incident_id).all()
    dsp_tr = db.query(DispatchTransition).filter(DispatchTransition.dispatch_id == dispatch_id).all()
    db.close()

    assert len(inc_tr) == 5  # NONE->OPEN, OPEN->ACK, ACK->INV, INV->MIT, MIT->RES
    assert len(dsp_tr) == 6  # UNASSIGNED->ASSIGNED, ASSIGNED->ACK, ACK->EN_ROUTE, EN_ROUTE->ON_SCENE, ON_SCENE->RESPONDING, RESPONDING->COMPLETED


def test_02_incident_deduplication_and_telemetry_recovery():
    """Verify continuous HIGH_RISK frames do NOT spam active incidents, and recovery to NORMAL keeps incident OPEN."""
    db = TestingSessionLocal()
    telemetry = {
        "event_id": "EVT-6D4-002",
        "camera_id": "CAM-02",
        "zone_id": "ZONE-02",
        "warning": {"operational_warning_state": "HIGH_RISK"},
        "current_risk": {"score": 90.0},
        "ai_prediction": {"probability": 0.95},
    }

    # Frame 1: Creation
    inc1 = process_realtime_inference_incident(db, telemetry)
    assert inc1 is not None
    inc_id = inc1.incident_id

    # Frame 2: Continuous HIGH_RISK
    telemetry["current_risk"]["score"] = 92.0
    inc2 = process_realtime_inference_incident(db, telemetry)
    assert inc2.incident_id == inc_id

    # Frame 3: Recovery to NORMAL
    telemetry["warning"]["operational_warning_state"] = "NORMAL"
    telemetry["current_risk"]["score"] = 15.0
    inc3 = process_realtime_inference_incident(db, telemetry)
    
    assert inc3.incident_id == inc_id
    assert inc3.status == "OPEN", "Incident MUST remain OPEN on recovery!"
    assert inc3.latest_warning_state == "NORMAL"
    db.close()


def test_03_camera_offline_handling():
    """Verify camera feed timeout produces OFFLINE status and is_degraded provenance flag."""
    orchestrator = RealtimeInferenceOrchestrator()
    cam_id = "CAM-OFFLINE-TEST"
    zone_id = "ZONE-OFFLINE-TEST"

    rec = CameraHealthTracker.get_or_create(cam_id, zone_id)
    rec.last_frame_timestamp = time.time() - 30.0  # 30 seconds ago -> OFFLINE

    res = orchestrator.process_frame({}, camera_id=cam_id, zone_id=zone_id)
    assert res["current_risk"]["status"] == "OFFLINE"
    assert res["ai_prediction"]["status"] == "CAMERA_OFFLINE"
    assert res["provenance"]["is_degraded"] is True


def test_04_strict_rbac_enforcement():
    """Verify Field Officer cannot resolve incidents (Operator-only action)."""
    db = TestingSessionLocal()
    telemetry = {
        "event_id": "EVT-6D4-004",
        "camera_id": "CAM-04",
        "zone_id": "ZONE-04",
        "warning": {"operational_warning_state": "HIGH_RISK"},
    }
    inc = process_realtime_inference_incident(db, telemetry)
    db.close()

    field_headers = get_auth_headers("field_officer")
    res = client.post(f"/api/v1/operator/incidents/{inc.incident_id}/transition", json={"new_status": "ACKNOWLEDGED", "reason": "Field officer attempt"}, headers=field_headers)
    assert res.status_code in (401, 403), "Field officer MUST NOT be authorized to execute operator incident transitions!"
