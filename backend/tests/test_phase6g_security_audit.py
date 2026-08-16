import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
try:
    from tests.conftest import TestingSessionLocal
except ImportError:
    from conftest import TestingSessionLocal

from app.core.security import create_access_token
from app.models.audit import AuditLog
from app.services.audit_service import log_action
from app.models.dispatch import DispatchAssignment

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
def cleanup_phase6g_db():
    db = TestingSessionLocal()
    try:
        db.query(AuditLog).delete()
        db.query(DispatchAssignment).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    yield
    db = TestingSessionLocal()
    try:
        db.query(AuditLog).delete()
        db.query(DispatchAssignment).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def test_01_request_correlation_header_injection():
    """Verify X-Request-ID header is propagated or generated on all HTTP responses."""
    res = client.get("/health")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    assert res.headers["X-Request-ID"].startswith("req_")

    # Custom request ID propagation
    custom_id = "req_custom_test_12345"
    res_custom = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res_custom.status_code == 200
    assert res_custom.headers["X-Request-ID"] == custom_id


def test_02_rbac_viewer_blocked_from_state_changes():
    """Verify VIEWER / CITIZEN role is blocked (HTTP 403) from state-changing endpoints."""
    viewer_headers = get_auth_headers("viewer")

    # Attempt event creation
    res_evt = client.post("/api/v1/admin/events", json={"name": "Test Event", "venue": "Main Arena"}, headers=viewer_headers)
    assert res_evt.status_code == 403

    # Attempt incident status transition
    res_inc = client.post("/api/v1/operator/incidents/INC-TEST-001/transition", json={"new_status": "ACKNOWLEDGED", "reason": "Test"}, headers=viewer_headers)
    assert res_inc.status_code == 403

    # Attempt dispatch creation
    res_dsp = client.post("/api/v1/operator/incidents/INC-TEST-001/dispatch", json={"officer_id": "FO-001"}, headers=viewer_headers)
    assert res_dsp.status_code == 403


def test_03_field_officer_resource_authorization_isolation():
    """Verify a Field Officer cannot access or transition another officer's explicit assignment."""
    db = TestingSessionLocal()

    officer_a_id = str(uuid4())
    officer_b_id = str(uuid4())
    dsp_id = "DSP-ISOLATION-001"

    # Create dispatch explicitly for Officer B
    dispatch = DispatchAssignment(
        dispatch_id=dsp_id,
        incident_id="INC-ISOLATION-001",
        event_id="EVT-01",
        officer_id=officer_b_id,
        assigned_by="OPERATOR",
        status="ASSIGNED"
    )
    db.add(dispatch)
    db.commit()
    db.close()

    # Officer A tries to transition Officer B's dispatch
    officer_a_headers = get_auth_headers("field_officer", user_id=officer_a_id)
    res = client.post(
        f"/api/v1/officers/dispatches/{dsp_id}/transition",
        json={"new_status": "ACKNOWLEDGED", "reason": "Unauthorized access test"},
        headers=officer_a_headers
    )
    assert res.status_code == 403
    assert "belongs to another field officer" in res.json()["detail"]



def test_04_audit_log_querying_and_filtering():
    """Verify admin audit log endpoint returns filtered records with Phase 6G rich metadata."""
    db = TestingSessionLocal()

    actor_uuid = uuid4()
    log_action(
        db=db,
        actor_id=actor_uuid,
        actor_role="admin",
        action="OVERRIDE_GATE",
        target="gate:GATE-NORTH-01",
        resource_type="gate",
        resource_id="GATE-NORTH-01",
        event_id="EVT-01",
        reason="Crowd pressure emergency relief",
        success=True,
        request_id="req_audit_test_001"
    )
    db.close()

    admin_headers = get_auth_headers("system_admin")
    res = client.get("/api/v1/admin/audit-logs?action=OVERRIDE_GATE", headers=admin_headers)
    assert res.status_code == 200
    logs = res.json()

    assert len(logs) >= 1
    log_item = logs[0]
    assert log_item["action"] == "OVERRIDE_GATE"
    assert log_item["actor_role"] == "admin"
    assert log_item["resource_type"] == "gate"
    assert log_item["request_id"] == "req_audit_test_001"
    assert log_item["success"] is True


def test_05_websocket_unauthorized_subscription_denied():
    """Verify WebSocket stream rejects unauthorized subscriptions with explicit HTTP 403 error payload."""
    viewer_token = create_access_token(user_id=str(uuid4()), email="viewer@crowdshield.ai", role="viewer")
    with client.websocket_connect(f"/api/v1/realtime/stream?token={viewer_token}") as websocket:
        # Subscribe to administrative stream with restricted camera ID
        websocket.send_json({
            "type": "subscribe",
            "camera_id": "CAM_ADMIN_ONLY_RESTRICTED",
            "zone_id": "ZONE-RESTRICTED",
            "event_id": "EVT-SECRET"
        })
        resp = websocket.receive_json()
        assert resp["type"] == "ERROR"
        assert resp["code"] == 403
        assert "Unauthorized subscription" in resp["detail"]

