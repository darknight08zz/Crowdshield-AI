import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from fastapi.testclient import TestClient

from app.main import app
try:
    from tests.conftest import TestingSessionLocal
except ImportError:
    from conftest import TestingSessionLocal

from app.core.security import create_access_token
from app.models.event import Event
from app.models.zone import Zone
from app.models.incident import Incident, IncidentTransition
from app.models.incident_report import IncidentReport
from app.models.audit import AuditLog

client = TestClient(app)


def get_admin_headers(role: str = "system_admin", user_id: str = None) -> dict:
    uid = user_id or str(uuid4())
    token = create_access_token(
        user_id=uid,
        email=f"{role}_{uid[:6]}@crowdshield.ai",
        role=role
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def cleanup_database():
    db = TestingSessionLocal()
    try:
        db.query(IncidentTransition).delete()
        db.query(IncidentReport).delete()
        db.query(Incident).delete()
        db.query(AuditLog).delete()
        db.query(Zone).delete()
        db.query(Event).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    yield
    db = TestingSessionLocal()
    try:
        db.query(IncidentTransition).delete()
        db.query(IncidentReport).delete()
        db.query(Incident).delete()
        db.query(AuditLog).delete()
        db.query(Zone).delete()
        db.query(Event).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def test_01_missing_event_id_returns_400():
    """TEST 1: Missing event_id in Admin Zone creation returns HTTP 400 Bad Request."""
    headers = get_admin_headers()
    payload = {
        "name": "Orphan Zone",
        "capacity": 500
    }
    res = client.post("/api/v1/admin/zones", json=payload, headers=headers)
    assert res.status_code == 400
    assert "event_id is required when creating a zone." in res.json()["detail"]

    db = TestingSessionLocal()
    assert db.query(Zone).count() == 0
    db.close()


def test_02_invalid_event_id_returns_400():
    """TEST 2: Invalid event_id format returns HTTP 400 Bad Request."""
    headers = get_admin_headers()
    payload = {
        "event_id": "not-a-valid-uuid",
        "name": "Invalid UUID Zone",
        "capacity": 500
    }
    res = client.post("/api/v1/admin/zones", json=payload, headers=headers)
    assert res.status_code == 400
    assert "Invalid event_id format." in res.json()["detail"]

    db = TestingSessionLocal()
    assert db.query(Zone).count() == 0
    db.close()


def test_03_nonexistent_event_id_returns_404():
    """TEST 3: Nonexistent event_id returns HTTP 404 Not Found."""
    headers = get_admin_headers()
    random_uuid = str(uuid4())
    payload = {
        "event_id": random_uuid,
        "name": "Nonexistent Event Zone",
        "capacity": 500
    }
    res = client.post("/api/v1/admin/zones", json=payload, headers=headers)
    assert res.status_code == 404
    assert "Parent Event not found." in res.json()["detail"]

    db = TestingSessionLocal()
    assert db.query(Zone).count() == 0
    db.close()


def test_04_valid_existing_event_creates_zone():
    """TEST 4: Valid existing event creates Zone linked to exact event_id."""
    db = TestingSessionLocal()
    event_id = uuid4()
    test_event = Event(
        id=event_id,
        name="Valid Admin Event",
        date=datetime.now(timezone.utc),
        venue="Main Arena",
        status="active"
    )
    db.add(test_event)
    db.commit()
    db.close()

    headers = get_admin_headers()
    payload = {
        "event_id": str(event_id),
        "name": "North Gate Zone",
        "capacity": 750
    }
    res = client.post("/api/v1/admin/zones", json=payload, headers=headers)
    assert res.status_code == 201
    res_data = res.json()
    assert res_data["event_id"] == str(event_id)
    assert res_data["name"] == "North Gate Zone"

    db = TestingSessionLocal()
    created_zone = db.query(Zone).filter(Zone.id == UUID(res_data["id"])).first()
    assert created_zone is not None
    assert created_zone.event_id == event_id
    db.close()


def test_05_ensure_no_arbitrary_fallback():
    """TEST 5: Ensure system does not fall back to any existing Event (Event A or Event B) when event_id is missing or invalid."""
    db = TestingSessionLocal()
    event_a_id = uuid4()
    event_b_id = uuid4()
    event_a = Event(id=event_a_id, name="Event A", date=datetime.now(timezone.utc), venue="Venue A", status="active")
    event_b = Event(id=event_b_id, name="Event B", date=datetime.now(timezone.utc), venue="Venue B", status="active")
    db.add(event_a)
    db.add(event_b)
    db.commit()
    db.close()

    headers = get_admin_headers()

    # Subtest 5.1: Missing event_id
    res_missing = client.post("/api/v1/admin/zones", json={"name": "Fallback Attempt Missing", "capacity": 300}, headers=headers)
    assert res_missing.status_code == 400

    # Subtest 5.2: Nonexistent event_id
    res_fake = client.post("/api/v1/admin/zones", json={"event_id": str(uuid4()), "name": "Fallback Attempt Fake", "capacity": 300}, headers=headers)
    assert res_fake.status_code == 404

    # Verify no Zone was attached to Event A or Event B
    db = TestingSessionLocal()
    assert db.query(Zone).count() == 0
    assert db.query(Zone).filter(Zone.event_id == event_a_id).count() == 0
    assert db.query(Zone).filter(Zone.event_id == event_b_id).count() == 0
    db.close()
