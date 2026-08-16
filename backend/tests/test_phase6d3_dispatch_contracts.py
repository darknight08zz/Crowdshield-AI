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
from app.models.dispatch import ResponseOfficer, DispatchAssignment, DispatchTransition
from app.services.incident_service import process_realtime_inference_incident
from app.services.dispatch_service import seed_default_officers_if_empty

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
def cleanup_dispatch_db():
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


def test_01_response_officer_listing():
    """Verify GET /api/v1/operator/response-officers returns registered officers."""
    headers = get_auth_headers("operator")
    res = client.get("/api/v1/operator/response-officers", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data) >= 3
    officer_ids = [o["officer_id"] for o in data]
    assert "FO-001" in officer_ids
    assert "FO-002" in officer_ids


def test_02_create_dispatch_contract():
    """Verify POST /api/v1/operator/incidents/{id}/dispatch creates a canonical assignment."""
    db = TestingSessionLocal()
    telemetry = {
        "event_id": "EVT-6D3-001",
        "zone_id": "ZONE-ALPHA",
        "camera_id": "CAM-01",
        "warning": {"operational_warning_state": "HIGH_RISK"},
        "current_risk": {"score": 88.0},
        "ai_prediction": {"probability": 0.92},
    }
    inc = process_realtime_inference_incident(db, telemetry)
    db.close()
    assert inc is not None

    headers = get_auth_headers("operator")
    payload = {
        "officer_id": "FO-001",
        "eta_minutes": 5,
        "reason": "Rapid crowd surge detected at North Entrance"
    }
    res = client.post(f"/api/v1/operator/incidents/{inc.incident_id}/dispatch", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["incident_id"] == inc.incident_id
    assert data["officer_id"] == "FO-001"
    assert data["status"] == "ASSIGNED"
    assert data["eta_minutes"] == 5
    assert len(data["transitions"]) >= 1
    assert data["transitions"][0]["previous_status"] == "UNASSIGNED"
    assert data["transitions"][0]["new_status"] == "ASSIGNED"


def test_03_duplicate_dispatch_protection():
    """Verify sending duplicate dispatch request returns existing active dispatch (idempotency)."""
    db = TestingSessionLocal()
    telemetry = {
        "event_id": "EVT-6D3-002",
        "zone_id": "ZONE-BETA",
        "camera_id": "CAM-02",
        "warning": {"operational_warning_state": "EARLY_WARNING"},
    }
    inc = process_realtime_inference_incident(db, telemetry)
    db.close()

    headers = get_auth_headers("operator")
    payload = {
        "officer_id": "FO-002",
        "eta_minutes": 7,
        "reason": "Initial field verification"
    }

    res1 = client.post(f"/api/v1/operator/incidents/{inc.incident_id}/dispatch", json=payload, headers=headers)
    assert res1.status_code == 200
    dsp1 = res1.json()

    # Second call for same officer & incident
    res2 = client.post(f"/api/v1/operator/incidents/{inc.incident_id}/dispatch", json=payload, headers=headers)
    assert res2.status_code == 200
    dsp2 = res2.json()

    assert dsp1["dispatch_id"] == dsp2["dispatch_id"]


def test_04_terminal_incident_dispatch_rejected():
    """Verify creating dispatch for a RESOLVED incident returns HTTP 400."""
    db = TestingSessionLocal()
    telemetry = {
        "event_id": "EVT-6D3-003",
        "zone_id": "ZONE-GAMMA",
        "camera_id": "CAM-03",
        "warning": {"operational_warning_state": "HIGH_RISK"},
    }
    inc = process_realtime_inference_incident(db, telemetry)
    db.close()

    headers = get_auth_headers("operator")

    # Move incident to RESOLVED first
    client.post(f"/api/v1/operator/incidents/{inc.incident_id}/transition", json={"new_status": "ACKNOWLEDGED", "reason": "Ack"}, headers=headers)
    client.post(f"/api/v1/operator/incidents/{inc.incident_id}/transition", json={"new_status": "INVESTIGATING", "reason": "Inv"}, headers=headers)
    client.post(f"/api/v1/operator/incidents/{inc.incident_id}/transition", json={"new_status": "MITIGATING", "reason": "Mit"}, headers=headers)
    client.post(f"/api/v1/operator/incidents/{inc.incident_id}/transition", json={"new_status": "RESOLVED", "reason": "Res"}, headers=headers)

    payload = {"officer_id": "FO-001", "eta_minutes": 5, "reason": "Late dispatch attempt"}
    res = client.post(f"/api/v1/operator/incidents/{inc.incident_id}/dispatch", json=payload, headers=headers)
    assert res.status_code == 400
    assert "Cannot create dispatch for terminal incident" in res.json()["detail"]


def test_05_valid_dispatch_state_transitions():
    """Verify dispatch lifecycle flow: ASSIGNED -> ACKNOWLEDGED -> EN_ROUTE -> ON_SCENE -> RESPONDING -> COMPLETED."""
    db = TestingSessionLocal()
    telemetry = {
        "event_id": "EVT-6D3-005",
        "zone_id": "ZONE-DELTA",
        "camera_id": "CAM-04",
        "warning": {"operational_warning_state": "HIGH_RISK"},
    }
    inc = process_realtime_inference_incident(db, telemetry)
    db.close()

    op_headers = get_auth_headers("operator")
    field_headers = get_auth_headers("field_officer")

    # Create dispatch
    d_res = client.post(f"/api/v1/operator/incidents/{inc.incident_id}/dispatch", json={"officer_id": "FO-001", "reason": "Dispatch unit"}, headers=op_headers)
    dsp_id = d_res.json()["dispatch_id"]

    # 1. ASSIGNED -> ACKNOWLEDGED
    r1 = client.post(f"/api/v1/officers/dispatches/{dsp_id}/transition", json={"new_status": "ACKNOWLEDGED", "reason": "Officer acknowledged"}, headers=field_headers)
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "ACKNOWLEDGED"

    # 2. ACKNOWLEDGED -> EN_ROUTE
    r2 = client.post(f"/api/v1/officers/dispatches/{dsp_id}/transition", json={"new_status": "EN_ROUTE", "reason": "Departed base"}, headers=field_headers)
    assert r2.status_code == 200
    assert r2.json()["status"] == "EN_ROUTE"

    # 3. EN_ROUTE -> ON_SCENE
    r3 = client.post(f"/api/v1/officers/dispatches/{dsp_id}/transition", json={"new_status": "ON_SCENE", "reason": "Arrived at Gate A"}, headers=field_headers)
    assert r3.status_code == 200
    assert r3.json()["status"] == "ON_SCENE"

    # 4. ON_SCENE -> RESPONDING
    r4 = client.post(f"/api/v1/officers/dispatches/{dsp_id}/transition", json={"new_status": "RESPONDING", "reason": "Opening relief exit gate"}, headers=field_headers)
    assert r4.status_code == 200
    assert r4.json()["status"] == "RESPONDING"

    # 5. RESPONDING -> COMPLETED
    r5 = client.post(f"/api/v1/officers/dispatches/{dsp_id}/transition", json={"new_status": "COMPLETED", "reason": "Flow restored to safe levels"}, headers=field_headers)
    assert r5.status_code == 200
    assert r5.json()["status"] == "COMPLETED"


def test_06_invalid_dispatch_transition_rejected():
    """Verify illegal jump ASSIGNED -> COMPLETED is rejected with 400."""
    db = TestingSessionLocal()
    telemetry = {
        "event_id": "EVT-6D3-006",
        "zone_id": "ZONE-EPSILON",
        "warning": {"operational_warning_state": "EARLY_WARNING"},
    }
    inc = process_realtime_inference_incident(db, telemetry)
    db.close()

    headers = get_auth_headers("operator")
    d_res = client.post(f"/api/v1/operator/incidents/{inc.incident_id}/dispatch", json={"officer_id": "FO-001", "reason": "Test illegal transition"}, headers=headers)
    dsp_id = d_res.json()["dispatch_id"]

    res = client.post(f"/api/v1/operator/dispatches/{dsp_id}/transition", json={"new_status": "COMPLETED", "reason": "Illegal jump"}, headers=headers)
    assert res.status_code == 400
    assert "Invalid dispatch status transition" in res.json()["detail"]


def test_07_dispatch_completion_does_not_auto_resolve_incident():
    """Verify completing a dispatch assignment leaves the parent incident in its current state (INVESTIGATING)."""
    db = TestingSessionLocal()
    telemetry = {
        "event_id": "EVT-6D3-007",
        "zone_id": "ZONE-ZETA",
        "warning": {"operational_warning_state": "HIGH_RISK"},
    }
    inc = process_realtime_inference_incident(db, telemetry)
    db.close()

    op_headers = get_auth_headers("operator")
    field_headers = get_auth_headers("field_officer")

    # Move incident to INVESTIGATING
    client.post(f"/api/v1/operator/incidents/{inc.incident_id}/transition", json={"new_status": "ACKNOWLEDGED", "reason": "Ack"}, headers=op_headers)
    client.post(f"/api/v1/operator/incidents/{inc.incident_id}/transition", json={"new_status": "INVESTIGATING", "reason": "Inv"}, headers=op_headers)

    # Dispatch & Complete officer action
    d_res = client.post(f"/api/v1/operator/incidents/{inc.incident_id}/dispatch", json={"officer_id": "FO-001", "reason": "Dispatch"}, headers=op_headers)
    dsp_id = d_res.json()["dispatch_id"]

    client.post(f"/api/v1/officers/dispatches/{dsp_id}/transition", json={"new_status": "ACKNOWLEDGED", "reason": "Ack"}, headers=field_headers)
    client.post(f"/api/v1/officers/dispatches/{dsp_id}/transition", json={"new_status": "EN_ROUTE", "reason": "En route"}, headers=field_headers)
    client.post(f"/api/v1/officers/dispatches/{dsp_id}/transition", json={"new_status": "ON_SCENE", "reason": "On scene"}, headers=field_headers)
    client.post(f"/api/v1/officers/dispatches/{dsp_id}/transition", json={"new_status": "RESPONDING", "reason": "Responding"}, headers=field_headers)
    client.post(f"/api/v1/officers/dispatches/{dsp_id}/transition", json={"new_status": "COMPLETED", "reason": "Completed"}, headers=field_headers)

    # Check parent incident status: MUST STILL BE INVESTIGATING
    inc_res = client.get(f"/api/v1/operator/incidents/{inc.incident_id}", headers=op_headers)
    assert inc_res.status_code == 200
    assert inc_res.json()["status"] == "INVESTIGATING"


def test_08_field_officer_assignment_context():
    """Verify GET /api/v1/officers/dispatches/{id} returns dispatch context with physics risk, AI probability, and disclaimer."""
    db = TestingSessionLocal()
    telemetry = {
        "event_id": "EVT-6D3-008",
        "zone_id": "ZONE-ETA",
        "warning": {"operational_warning_state": "HIGH_RISK"},
        "current_risk": {"score": 82.5},
        "ai_prediction": {"probability": 0.89},
    }
    inc = process_realtime_inference_incident(db, telemetry)
    db.close()

    headers = get_auth_headers("operator")
    d_res = client.post(f"/api/v1/operator/incidents/{inc.incident_id}/dispatch", json={"officer_id": "FO-001", "reason": "Context check"}, headers=headers)
    dsp_id = d_res.json()["dispatch_id"]

    field_headers = get_auth_headers("field_officer")
    ctx_res = client.get(f"/api/v1/officers/dispatches/{dsp_id}", headers=field_headers)
    assert ctx_res.status_code == 200, ctx_res.text
    ctx = ctx_res.json()

    assert ctx["dispatch"]["dispatch_id"] == dsp_id
    assert ctx["incident_id"] == inc.incident_id
    assert ctx["zone_id"] == "ZONE-ETA"
    assert ctx["physics_risk"] == 82.5
    assert ctx["ai_probability"] == 0.89
    assert ctx["model_version"] == "v2.0.0"
    assert ctx["disclaimer"] == "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated."


def test_09_unauthorized_access_returns_401():
    """Verify unauthenticated requests return HTTP 401."""
    res = client.get("/api/v1/operator/response-officers")
    assert res.status_code in (401, 403)
