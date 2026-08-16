import sys
import os
import time

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.ai.services.realtime_result_store import inference_result_store
from app.ai.services.inference_orchestrator import RealtimeInferenceResult

@pytest.fixture
def auth_token():
    return create_access_token(user_id="operator_test_user", email="op@crowdshield.io", role="operator")

@pytest.fixture
def store():
    inference_result_store.clear_all()
    yield inference_result_store
    inference_result_store.clear_all()

def create_sample_result(
    camera_id: str = "CAM-6C1",
    zone_id: str = "ZONE-6C1",
    event_id: str = "EVT-6C1",
    risk_score: float = 68.5,
    ai_prob: float = 0.73,
    warning_state: str = "EARLY_WARNING",
    timestamp: str = None,
):
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()
        
    return RealtimeInferenceResult.create(
        timestamp=timestamp,
        event_id=event_id,
        camera_id=camera_id,
        zone_id=zone_id,
        camera_health={"status": "ONLINE", "is_degraded": False, "detection_success_rate": 0.98},
        telemetry={
            "density": 2.1,
            "average_speed": 0.48,
            "median_speed": 0.50,
            "inflow_rate": 58.0,
            "outflow_rate": 17.0,
            "flow_imbalance": 41.0,
            "net_accumulation": 100.0,
            "person_count": 1850,
            "tracked_person_count": 1850,
            "direction_conflict_score": 0.35,
            "reverse_flow_ratio": 0.12,
            "blockage_score": 0.20,
            "is_degraded": False,
            "calibration_status": "HOMOGRAPHY"
        },
        current_risk={"score": risk_score, "bucket": "HIGH", "status": "SUCCESS"},
        ai_prediction={
            "status": "SUCCESS",
            "prediction_status": "SUCCESS",
            "model_version": "v2.0.0",
            "target": "EARLY_ESCALATION_5M",
            "horizon_seconds": 300,
            "probability": ai_prob,
            "history_ready": True,
            "available_history_steps": 30
        },
        warning={
            "operational_warning_state": warning_state,
            "raw_candidate_state": warning_state,
            "warning_timestamp": timestamp
        },
        provenance={
            "event_id": event_id,
            "camera_id": camera_id,
            "zone_id": zone_id,
            "processing_mode": "LIVE",
            "telemetry_source": "live_cctv_gps",
            "calibration_status": "HOMOGRAPHY",
            "telemetry_timestamp": timestamp,
            "prediction_timestamp": timestamp,
            "warning_timestamp": timestamp,
            "model_version": "v2.0.0-prototype",
            "disclaimer": "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated."
        }
    )

def test_6c1_rest_snapshot_fetch(store, auth_token):
    """Verify REST snapshot endpoints return Phase 6B canonical data for frontend initial load."""
    result = create_sample_result()
    store.update_result(result)
    client = TestClient(app)
    auth_headers = {"Authorization": f"Bearer {auth_token}"}

    # Test camera-level snapshot
    res_cam = client.get(f"/api/v1/operator/cameras/{result['camera_id']}/inference", headers=auth_headers)
    assert res_cam.status_code == 200
    data_cam = res_cam.json()
    assert data_cam["camera_id"] == "CAM-6C1"
    assert data_cam["current_physics_risk"] == 68.5
    assert data_cam["ai_probability"] == 0.73
    assert data_cam["operational_warning_state"] == "EARLY_WARNING"
    assert data_cam["person_count"] == 1850

    # Test zone-level snapshot
    res_zone = client.get(f"/api/v1/operator/cameras/{result['camera_id']}/zones/{result['zone_id']}/inference", headers=auth_headers)
    assert res_zone.status_code == 200
    data_zone = res_zone.json()
    assert data_zone["zone_id"] == "ZONE-6C1"
    assert data_zone["density"] == 2.1
    assert data_zone["disclaimer"].startswith("AI Early Warning")

def test_6c1_websocket_auth_and_subscription(auth_token, store):
    """Verify WebSocket connection, authentication, subscription, and live streaming delivery."""
    result = create_sample_result()
    client = TestClient(app)

    with client.websocket_connect(f"/api/v1/realtime/stream?token={auth_token}") as websocket:
        # Subscribe to camera stream
        websocket.send_json({
            "type": "subscribe",
            "event_id": result["event_id"],
            "camera_id": result["camera_id"],
            "zone_id": result["zone_id"],
        })
        
        # Confirmation frame
        conf = websocket.receive_json()
        assert conf["type"] == "SUBSCRIPTION_CONFIRMED"
        assert conf["camera_id"] == result["camera_id"]

        # Publish new telemetry via store & WS publish_test
        store.update_result(result)
        websocket.send_json({"type": "publish_test", "payload": result})

        # Receive live update frame
        update = websocket.receive_json()
        assert update["type"] == "INFERENCE_UPDATE"
        assert update["data"]["camera_id"] == result["camera_id"]
        assert update["data"]["current_physics_risk"] == 68.5
        assert update["data"]["operational_warning_state"] == "EARLY_WARNING"

def test_6c1_subscription_switching_isolation(auth_token, store):
    """Verify that switching subscriptions correctly isolates data feeds without cross-contamination."""
    client = TestClient(app)
    
    result_a = create_sample_result(camera_id="CAM-A", zone_id="ZONE-A", risk_score=30.0, ai_prob=0.2, warning_state="NORMAL")
    result_b = create_sample_result(camera_id="CAM-B", zone_id="ZONE-B", risk_score=85.0, ai_prob=0.9, warning_state="HIGH_RISK")

    with client.websocket_connect(f"/api/v1/realtime/stream?token={auth_token}") as websocket:
        # Subscribe to CAM-A
        websocket.send_json({"type": "subscribe", "event_id": "EVT-6C1", "camera_id": "CAM-A", "zone_id": "ZONE-A"})
        websocket.receive_json() # confirmation

        # Broadcast update for CAM-A
        websocket.send_json({"type": "publish_test", "payload": result_a})
        update = websocket.receive_json()
        assert update["type"] == "INFERENCE_UPDATE"
        assert update["data"]["camera_id"] == "CAM-A"
        assert update["data"]["current_physics_risk"] == 30.0

        # Unsubscribe CAM-A and subscribe to CAM-B
        websocket.send_json({"type": "unsubscribe"})
        unsub_resp = websocket.receive_json()
        assert unsub_resp["type"] == "UNSUBSCRIBE_CONFIRMED"

        websocket.send_json({"type": "subscribe", "event_id": "EVT-6C1", "camera_id": "CAM-B", "zone_id": "ZONE-B"})
        sub_b_resp = websocket.receive_json() # confirmation CAM-B
        assert sub_b_resp["type"] == "SUBSCRIPTION_CONFIRMED"
        assert sub_b_resp["camera_id"] == "CAM-B"

        # Broadcast update for CAM-B
        websocket.send_json({"type": "publish_test", "payload": result_b})
        update_b = websocket.receive_json()
        assert update_b["type"] == "INFERENCE_UPDATE"
        assert update_b["data"]["camera_id"] == "CAM-B"
        assert update_b["data"]["current_physics_risk"] == 85.0

def test_6c1_stale_and_degraded_state_handling(store, auth_token):
    """Verify that old/stale telemetry results return is_stale: True and camera_health_status: OFFLINE."""
    stale_result = create_sample_result(camera_id="CAM-OFFLINE", zone_id="ZONE-OFFLINE")

    store.update_result(stale_result)
    
    # Force stale timestamp in result store
    key = (stale_result["event_id"], stale_result["camera_id"], stale_result["zone_id"])
    inference_result_store._last_update_ts[key] = time.monotonic() - 20.0

    client = TestClient(app)
    auth_headers = {"Authorization": f"Bearer {auth_token}"}

    res = client.get("/api/v1/operator/cameras/CAM-OFFLINE/inference", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_stale"] is True
    assert data["camera_health_status"] == "OFFLINE"
