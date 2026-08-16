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
from app.services.incident_service import process_realtime_inference_incident, transition_incident_status

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
def cleanup_incidents_db():
    db = TestingSessionLocal()
    try:
        db.query(IncidentTransition).delete()
        db.query(Incident).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    yield
    db = TestingSessionLocal()
    try:
        db.query(IncidentTransition).delete()
        db.query(Incident).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def test_01_canonical_incidents_list_contract():
    """Verify GET /api/v1/operator/incidents returns canonical response objects."""
    db = TestingSessionLocal()
    telemetry = {
        "event_id": "EVT-6D2-001",
        "zone_id": "ZONE-ALPHA",
        "camera_id": "CAM-01",
        "telemetry_timestamp": "2026-08-16T12:00:00Z",
        "prediction_timestamp": "2026-08-16T12:05:00Z",
        "warning": {
            "operational_warning_state": "HIGH_RISK",
        },
        "current_risk": {
            "score": 85.5,
        },
        "ai_prediction": {
            "probability": 0.88,
        },
        "camera_health": {
            "status": "ONLINE",
        },
        "is_stale": False,
        "is_degraded": False,
    }
    inc = process_realtime_inference_incident(db, telemetry)
    db.close()
    assert inc is not None

    headers = get_auth_headers("operator")
    res = client.get("/api/v1/operator/incidents", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data) >= 1

    first = data[0]
    assert "incident_id" in first
    assert first["event_id"] == "EVT-6D2-001"
    assert first["zone_id"] == "ZONE-ALPHA"
    assert first["status"] == "OPEN"
    assert "creation_snapshot" in first
    assert "latest_snapshot" in first
    assert "provenance" in first
    assert first["creation_snapshot"]["physics_risk_at_creation"] == 85.5
    assert first["creation_snapshot"]["ai_probability_at_creation"] == 0.88
    assert first["provenance"]["disclaimer"] == "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated."


def test_02_canonical_incident_detail_contract():
    """Verify GET /api/v1/operator/incidents/{incident_id} retrieves details & transitions."""
    db = TestingSessionLocal()
    telemetry = {
        "event_id": "EVT-6D2-002",
        "zone_id": "ZONE-BETA",
        "camera_id": "CAM-02",
        "telemetry_timestamp": "2026-08-16T12:00:00Z",
        "warning": {
            "operational_warning_state": "EARLY_WARNING",
        },
        "current_risk": {
            "score": 65.0,
        },
        "ai_prediction": {
            "probability": 0.72,
        },
        "camera_health": {
            "status": "ONLINE",
        },
    }
    inc = process_realtime_inference_incident(db, telemetry)
    db.close()
    assert inc is not None

    headers = get_auth_headers("operator")
    res = client.get(f"/api/v1/operator/incidents/{inc.incident_id}", headers=headers)
    assert res.status_code == 200, res.text
    detail = res.json()
    assert detail["incident_id"] == inc.incident_id
    assert detail["status"] == "OPEN"
    assert len(detail["transitions"]) >= 1
    assert detail["transitions"][0]["actor_type"] == "SYSTEM"


def test_03_transition_api_workflow_contract():
    """Verify operator lifecycle state transitions execute correctly."""
    db = TestingSessionLocal()
    telemetry = {
        "event_id": "EVT-6D2-003",
        "zone_id": "ZONE-GAMMA",
        "camera_id": "CAM-03",
        "warning": {
            "operational_warning_state": "HIGH_RISK",
        },
        "current_risk": {
            "score": 90.0,
        },
        "ai_prediction": {
            "probability": 0.95,
        },
    }
    inc = process_realtime_inference_incident(db, telemetry)
    db.close()
    assert inc is not None

    headers = get_auth_headers("operator")

    # 1. OPEN -> ACKNOWLEDGED
    res1 = client.post(
        f"/api/v1/operator/incidents/{inc.incident_id}/transition",
        json={"new_status": "ACKNOWLEDGED", "reason": "Operator confirmed warning"},
        headers=headers
    )
    assert res1.status_code == 200, res1.text
    assert res1.json()["status"] == "ACKNOWLEDGED"

    # 2. ACKNOWLEDGED -> INVESTIGATING
    res2 = client.post(
        f"/api/v1/operator/incidents/{inc.incident_id}/transition",
        json={"new_status": "INVESTIGATING", "reason": "Field team dispatched"},
        headers=headers
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "INVESTIGATING"

    # 3. INVESTIGATING -> MITIGATING
    res3 = client.post(
        f"/api/v1/operator/incidents/{inc.incident_id}/transition",
        json={"new_status": "MITIGATING", "reason": "Barricades reconfigured"},
        headers=headers
    )
    assert res3.status_code == 200
    assert res3.json()["status"] == "MITIGATING"

    # 4. MITIGATING -> RESOLVED
    res4 = client.post(
        f"/api/v1/operator/incidents/{inc.incident_id}/transition",
        json={"new_status": "RESOLVED", "reason": "Crowd density stabilized"},
        headers=headers
    )
    assert res4.status_code == 200
    assert res4.json()["status"] == "RESOLVED"
    assert res4.json()["resolution_notes"] == "Crowd density stabilized"


def test_04_invalid_transition_returns_400():
    """Verify invalid state transitions return HTTP 400 Bad Request."""
    db = TestingSessionLocal()
    telemetry = {
        "event_id": "EVT-6D2-004",
        "zone_id": "ZONE-DELTA",
        "camera_id": "CAM-04",
        "warning": {
            "operational_warning_state": "EARLY_WARNING",
        },
    }
    inc = process_realtime_inference_incident(db, telemetry)
    db.close()
    assert inc is not None

    headers = get_auth_headers("operator")

    # Invalid jump OPEN -> RESOLVED
    res = client.post(
        f"/api/v1/operator/incidents/{inc.incident_id}/transition",
        json={"new_status": "RESOLVED", "reason": "Illegal jump"},
        headers=headers
    )
    assert res.status_code == 400
    assert "Invalid state transition" in res.json()["detail"]


def test_05_unauthorized_access_returns_401():
    """Verify requests without auth token return 401 Unauthorized."""
    res = client.get("/api/v1/operator/incidents")
    assert res.status_code in (401, 403)
