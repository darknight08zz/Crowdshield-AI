import pytest
from datetime import datetime, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
try:
    from tests.conftest import TestingSessionLocal
except ImportError:
    from conftest import TestingSessionLocal
from app.core.security import create_access_token
from app.models.incident import Incident, IncidentTransition
from app.services.incident_service import (
    evaluate_incident_policy,
    process_realtime_inference_incident,
    transition_incident_status,
    VALID_TRANSITIONS,
)

client = TestClient(app)


def get_auth_headers(role: str = "operator", user_id: str = None) -> dict:
    uid = user_id or str(uuid4())
    token = create_access_token(
        user_id=uid,
        email=f"{role}@crowdshield.ai",
        role=role
    )
    return {"Authorization": f"Bearer {token}", "X-User-ID": uid}


def get_db_session() -> Session:
    return TestingSessionLocal()


# ============================================================================
# 1. INCIDENT CREATION POLICY CONTRACTS
# ============================================================================

def test_01_incident_policy_evaluation():
    """Verifies that EARLY_WARNING and HIGH_RISK trigger policy, while NORMAL and WATCH are ignored."""
    assert evaluate_incident_policy("EARLY_WARNING") is True
    assert evaluate_incident_policy("HIGH_RISK") is True
    assert evaluate_incident_policy("early_warning") is True
    assert evaluate_incident_policy("high_risk") is True

    assert evaluate_incident_policy("NORMAL") is False
    assert evaluate_incident_policy("WATCH") is False
    assert evaluate_incident_policy("SAFE") is False


def test_02_realtime_telemetry_triggers_new_incident():
    """Verifies that an EARLY_WARNING telemetry frame creates a canonical incident record with snapshots."""
    db = get_db_session()
    try:
        telemetry = {
            "event_id": "evt_01",
            "camera_id": "CAM-01",
            "zone_id": "z-1",
            "telemetry_timestamp": "2026-08-16T12:00:00Z",
            "prediction_timestamp": "2026-08-16T12:05:00Z",
            "warning": {
                "operational_warning_state": "EARLY_WARNING",
            },
            "current_risk": {
                "score": 0.72,
            },
            "ai_prediction": {
                "probability": 0.85,
            },
            "camera_health": {
                "status": "ONLINE",
            },
            "is_stale": False,
            "is_degraded": False,
        }

        incident = process_realtime_inference_incident(db, telemetry)
        assert incident is not None
        assert incident.incident_id.startswith("INC-")
        assert incident.event_id == "evt_01"
        assert incident.camera_id == "CAM-01"
        assert incident.zone_id == "z-1"
        assert incident.status == "OPEN"
        assert incident.source_type == "AI_EARLY_WARNING_PROXY"

        # Check creation snapshot
        assert incident.warning_state_at_creation == "EARLY_WARNING"
        assert incident.physics_risk_at_creation == 0.72
        assert incident.ai_probability_at_creation == 0.85

        # Check provenance disclaimers
        assert incident.model_version == "v2.0.0"
        assert incident.prediction_target == "EARLY_ESCALATION_5M"
        assert incident.model_status == "PROTOTYPE"
        assert "Prototype" in incident.disclaimer

        # Check SYSTEM transition log
        transitions = db.query(IncidentTransition).filter(IncidentTransition.incident_id == incident.incident_id).all()
        assert len(transitions) == 1
        assert transitions[0].previous_status == "NONE"
        assert transitions[0].new_status == "OPEN"
        assert transitions[0].actor_type == "SYSTEM"
    finally:
        db.close()


def test_03_deduplication_active_incident_correlation():
    """
    Verifies that subsequent HIGH_RISK telemetry frames for the same (event_id, camera_id, zone_id)
    update the active incident's latest context without creating a duplicate active incident.
    """
    db = get_db_session()
    try:
        t1 = {
            "event_id": "evt_01",
            "camera_id": "CAM-02",
            "zone_id": "z-2",
            "telemetry_timestamp": "2026-08-16T12:10:00Z",
            "warning": {"operational_warning_state": "HIGH_RISK"},
            "current_risk": {"score": 0.81},
            "ai_prediction": {"probability": 0.90},
        }

        inc1 = process_realtime_inference_incident(db, t1)
        assert inc1 is not None
        inc1_id = inc1.incident_id

        # Second telemetry frame with higher risk
        t2 = {
            "event_id": "evt_01",
            "camera_id": "CAM-02",
            "zone_id": "z-2",
            "telemetry_timestamp": "2026-08-16T12:11:00Z",
            "warning": {"operational_warning_state": "HIGH_RISK"},
            "current_risk": {"score": 0.95},
            "ai_prediction": {"probability": 0.98},
        }

        inc2 = process_realtime_inference_incident(db, t2)
        assert inc2 is not None
        assert inc2.incident_id == inc1_id  # Same incident, deduplicated

        # Verify creation snapshot is preserved vs latest context updated
        assert inc2.physics_risk_at_creation == 0.81
        assert inc2.latest_physics_risk == 0.95
        assert inc2.latest_ai_probability == 0.98

        # Count active incidents for zone z-2
        active_count = db.query(Incident).filter(
            Incident.zone_id == "z-2",
            Incident.status == "OPEN"
        ).count()
        assert active_count == 1
    finally:
        db.close()


def test_04_telemetry_recovery_does_not_auto_resolve_incident():
    """
    Verifies that when telemetry drops to NORMAL, the active incident latest context updates
    to NORMAL, but its lifecycle status remains OPEN (human-in-the-loop requirement).
    """
    db = get_db_session()
    try:
        t_surge = {
            "event_id": "evt_01",
            "camera_id": "CAM-03",
            "zone_id": "z-3",
            "warning": {"operational_warning_state": "HIGH_RISK"},
            "current_risk": {"score": 0.88},
        }
        inc = process_realtime_inference_incident(db, t_surge)
        assert inc.status == "OPEN"

        t_recovered = {
            "event_id": "evt_01",
            "camera_id": "CAM-03",
            "zone_id": "z-3",
            "warning": {"operational_warning_state": "NORMAL"},
            "current_risk": {"score": 0.20},
        }
        inc_after = process_realtime_inference_incident(db, t_recovered)
        assert inc_after is not None
        assert inc_after.incident_id == inc.incident_id
        assert inc_after.latest_warning_state == "NORMAL"
        assert inc_after.latest_physics_risk == 0.20
        assert inc_after.status == "OPEN"  # Not auto-resolved!
    finally:
        db.close()


# ============================================================================
# 2. DETERMINISTIC STATE MACHINE & AUDIT LOG CONTRACTS
# ============================================================================

def test_05_valid_state_transitions_flow():
    """Tests full valid transition chain: OPEN -> ACKNOWLEDGED -> INVESTIGATING -> MITIGATING -> RESOLVED."""
    db = get_db_session()
    try:
        t_init = {
            "event_id": "evt_01",
            "camera_id": "CAM-04",
            "zone_id": "z-4",
            "warning": {"operational_warning_state": "HIGH_RISK"},
            "current_risk": {"score": 0.85},
        }
        inc = process_realtime_inference_incident(db, t_init)
        inc_id = inc.incident_id

        # 1. ACKNOWLEDGED
        inc_ack = transition_incident_status(db, inc_id, "ACKNOWLEDGED", actor_id="op_101", reason="Checking camera feed")
        assert inc_ack.status == "ACKNOWLEDGED"
        assert inc_ack.acknowledged_by == "op_101"
        assert inc_ack.acknowledged_at is not None

        # 2. INVESTIGATING
        inc_inv = transition_incident_status(db, inc_id, "INVESTIGATING", actor_id="op_101", reason="Dispatching officer")
        assert inc_inv.status == "INVESTIGATING"

        # 3. MITIGATING
        inc_mit = transition_incident_status(db, inc_id, "MITIGATING", actor_id="op_101", reason="Opening secondary exit gate")
        assert inc_mit.status == "MITIGATING"

        # 4. RESOLVED
        inc_res = transition_incident_status(db, inc_id, "RESOLVED", actor_id="op_101", reason="Crowd density normalized")
        assert inc_res.status == "RESOLVED"
        assert inc_res.resolved_by == "op_101"
        assert inc_res.resolution_type == "RESOLVED"
        assert inc_res.resolved_at is not None

        # Verify Transition Audit History
        transitions = db.query(IncidentTransition).filter(IncidentTransition.incident_id == inc_id).order_by(IncidentTransition.timestamp.asc()).all()
        assert len(transitions) == 5  # 1 SYSTEM + 4 OPERATOR
        statuses = [tr.new_status for tr in transitions]
        assert statuses == ["OPEN", "ACKNOWLEDGED", "INVESTIGATING", "MITIGATING", "RESOLVED"]
    finally:
        db.close()


def test_06_invalid_state_transition_raises_error():
    """Verifies that invalid transitions (e.g. OPEN -> INVESTIGATING) raise ValueError."""
    db = get_db_session()
    try:
        t_init = {
            "event_id": "evt_01",
            "camera_id": "CAM-05",
            "zone_id": "z-5",
            "warning": {"operational_warning_state": "EARLY_WARNING"},
            "current_risk": {"score": 0.70},
        }
        inc = process_realtime_inference_incident(db, t_init)

        with pytest.raises(ValueError) as exc_info:
            transition_incident_status(db, inc.incident_id, "INVESTIGATING", actor_id="op_101")
        assert "Invalid state transition" in str(exc_info.value)
    finally:
        db.close()


def test_07_terminal_state_is_locked():
    """Verifies that once an incident is RESOLVED or FALSE_POSITIVE, no further transitions are allowed."""
    db = get_db_session()
    try:
        t_init = {
            "event_id": "evt_01",
            "camera_id": "CAM-06",
            "zone_id": "z-6",
            "warning": {"operational_warning_state": "EARLY_WARNING"},
            "current_risk": {"score": 0.70},
        }
        inc = process_realtime_inference_incident(db, t_init)

        # Transition directly to FALSE_POSITIVE
        inc_fp = transition_incident_status(db, inc.incident_id, "FALSE_POSITIVE", actor_id="op_102", reason="Sensor glare")
        assert inc_fp.status == "FALSE_POSITIVE"

        # Attempt transition from terminal state
        with pytest.raises(ValueError) as exc_info:
            transition_incident_status(db, inc.incident_id, "ACKNOWLEDGED", actor_id="op_102")
        assert "terminal state" in str(exc_info.value).lower()
    finally:
        db.close()


def test_08_subsequent_surge_creates_new_incident_after_resolution():
    """Verifies that once an incident is RESOLVED, a new telemetry surge creates a NEW incident."""
    db = get_db_session()
    try:
        t1 = {
            "event_id": "evt_01",
            "camera_id": "CAM-07",
            "zone_id": "z-7",
            "warning": {"operational_warning_state": "HIGH_RISK"},
            "current_risk": {"score": 0.85},
        }
        inc1 = process_realtime_inference_incident(db, t1)
        transition_incident_status(db, inc1.incident_id, "ACKNOWLEDGED", actor_id="op_103")
        transition_incident_status(db, inc1.incident_id, "RESOLVED", actor_id="op_103", reason="Resolved first surge")

        # Second surge in same zone
        t2 = {
            "event_id": "evt_01",
            "camera_id": "CAM-07",
            "zone_id": "z-7",
            "warning": {"operational_warning_state": "HIGH_RISK"},
            "current_risk": {"score": 0.89},
        }
        inc2 = process_realtime_inference_incident(db, t2)
        assert inc2 is not None
        assert inc2.incident_id != inc1.incident_id
        assert inc2.status == "OPEN"
    finally:
        db.close()


# ============================================================================
# 3. REST API ENDPOINT CONTRACTS (/api/v1/operator/incidents)
# ============================================================================

def test_09_list_operator_incidents_api():
    """GET /api/v1/operator/incidents returns list of canonical incident objects."""
    headers = get_auth_headers("operator")
    response = client.get("/api/v1/operator/incidents", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        inc = data[0]
        assert "incident_id" in inc
        assert "creation_snapshot" in inc
        assert "latest_snapshot" in inc
        assert "provenance" in inc
        assert "disclaimer" in inc["provenance"]


def test_10_get_operator_incident_detail_api():
    """GET /api/v1/operator/incidents/{incident_id} returns detail with full transition audit log."""
    db = get_db_session()
    try:
        t_init = {
            "event_id": "evt_01",
            "camera_id": "CAM-08",
            "zone_id": "z-8",
            "warning": {"operational_warning_state": "HIGH_RISK"},
            "current_risk": {"score": 0.88},
        }
        inc = process_realtime_inference_incident(db, t_init)
        inc_id = inc.incident_id
    finally:
        db.close()

    headers = get_auth_headers("operator")
    response = client.get(f"/api/v1/operator/incidents/{inc_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == inc_id
    assert data["status"] == "OPEN"
    assert "transitions" in data
    assert len(data["transitions"]) >= 1


def test_11_post_transition_incident_api():
    """POST /api/v1/operator/incidents/{incident_id}/transition transitions state cleanly."""
    db = get_db_session()
    try:
        t_init = {
            "event_id": "evt_01",
            "camera_id": "CAM-09",
            "zone_id": "z-9",
            "warning": {"operational_warning_state": "EARLY_WARNING"},
            "current_risk": {"score": 0.75},
        }
        inc = process_realtime_inference_incident(db, t_init)
        inc_id = inc.incident_id
    finally:
        db.close()

    headers = get_auth_headers("operator", user_id="usr_op_99")
    payload = {
        "new_status": "ACKNOWLEDGED",
        "reason": "Operator confirmed visual warning on feed."
    }
    response = client.post(f"/api/v1/operator/incidents/{inc_id}/transition", headers=headers, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACKNOWLEDGED"
    assert data["acknowledged_by"] == "usr_op_99"
    assert len(data["transitions"]) == 2
    assert data["transitions"][1]["actor_id"] == "usr_op_99"
    assert data["transitions"][1]["new_status"] == "ACKNOWLEDGED"


def test_12_post_invalid_transition_api_returns_400():
    """POST with invalid transition returns HTTP 400 Bad Request."""
    db = get_db_session()
    try:
        t_init = {
            "event_id": "evt_01",
            "camera_id": "CAM-10",
            "zone_id": "z-10",
            "warning": {"operational_warning_state": "EARLY_WARNING"},
            "current_risk": {"score": 0.75},
        }
        inc = process_realtime_inference_incident(db, t_init)
        inc_id = inc.incident_id
    finally:
        db.close()

    headers = get_auth_headers("operator")
    payload = {"new_status": "INVESTIGATING", "reason": "Invalid shortcut"}
    response = client.post(f"/api/v1/operator/incidents/{inc_id}/transition", headers=headers, json=payload)
    assert response.status_code == 400
    assert "Invalid state transition" in response.json()["detail"]


def test_13_post_non_existent_incident_returns_404():
    """POST transition for non-existent incident returns HTTP 404 Not Found."""
    headers = get_auth_headers("operator")
    payload = {"new_status": "ACKNOWLEDGED"}
    response = client.post("/api/v1/operator/incidents/INC-DOES-NOT-EXIST/transition", headers=headers, json=payload)
    assert response.status_code == 404
