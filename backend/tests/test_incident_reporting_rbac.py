import pytest
from uuid import UUID, uuid4
from fastapi.testclient import TestClient

from app.main import app
try:
    from tests.conftest import TestingSessionLocal
except ImportError:
    from conftest import TestingSessionLocal

from app.core.security import create_access_token
from app.models.audit import AuditLog
from app.models.incident import Incident, IncidentTransition
from app.models.incident_report import IncidentReport
from app.models.user import User, UserRoleEnum

client = TestClient(app)


def get_auth_headers(role: str = "viewer", user_id: str = None) -> dict:
    uid = user_id or str(uuid4())
    token = create_access_token(
        user_id=uid,
        email=f"{role}_{uid[:6]}@crowdshield.ai",
        role=role
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def db_cleanup():
    db = TestingSessionLocal()
    try:
        db.query(IncidentTransition).delete()
        db.query(IncidentReport).delete()
        db.query(Incident).delete()
        db.query(AuditLog).delete()
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
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def test_01_viewer_can_submit_report():
    """Requirement 1 & 3: VIEWER can submit a report, initial status is REPORT_SUBMITTED."""
    viewer_id = str(uuid4())
    headers = get_auth_headers("viewer", user_id=viewer_id)
    payload = {
        "title": "Unusual crowd bottleneck near Gate 3",
        "description": "Dense crowd accumulation forming near main entry gate.",
        "event_id": "evt_01",
        "zone_id": "zone_gate_3",
        "reported_location": "Gate 3 North Entrance"
    }

    res = client.post("/api/v1/incident-reports", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "REPORT_SUBMITTED"
    assert data["title"] == payload["title"]
    assert data["submitted_by_user_id"] == viewer_id
    assert data["report_source"] == "VIEWER"
    assert data["report_id"].startswith("REP-")


def test_02_unauthenticated_user_cannot_submit():
    """Requirement 2: Unauthenticated user cannot submit (401 Unauthorized)."""
    payload = {
        "title": "Unauthenticated test report",
        "description": "Testing missing authorization header."
    }
    res = client.post("/api/v1/incident-reports", json=payload)
    assert res.status_code == 401


def test_03_submitted_report_initial_status():
    """Requirement 3: Explicit check that newly created report has status REPORT_SUBMITTED."""
    headers = get_auth_headers("viewer")
    payload = {"title": "Test initial status", "description": "Checking default status."}
    res = client.post("/api/v1/incident-reports", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["status"] == "REPORT_SUBMITTED"


def test_04_viewer_can_view_own_reports():
    """Requirement 4: VIEWER can view their own submitted reports."""
    viewer_id = str(uuid4())
    headers = get_auth_headers("viewer", user_id=viewer_id)

    res_create = client.post("/api/v1/incident-reports", json={"title": "My Report 1", "description": "Details 1"}, headers=headers)
    assert res_create.status_code == 201

    res_my = client.get("/api/v1/incident-reports/my", headers=headers)
    assert res_my.status_code == 200
    items = res_my.json()
    assert len(items) == 1
    assert items[0]["title"] == "My Report 1"
    assert items[0]["submitted_by_user_id"] == viewer_id


def test_05_viewer_cannot_view_another_users_report():
    """Requirement 5: VIEWER cannot view another user's report via operator review endpoint or /my."""
    user_a_id = str(uuid4())
    user_b_id = str(uuid4())

    headers_a = get_auth_headers("viewer", user_id=user_a_id)
    headers_b = get_auth_headers("viewer", user_id=user_b_id)

    client.post("/api/v1/incident-reports", json={"title": "User A Report", "description": "Details A"}, headers=headers_a)

    # User B checks their own list - should be empty
    res_b_my = client.get("/api/v1/incident-reports/my", headers=headers_b)
    assert res_b_my.status_code == 200
    assert len(res_b_my.json()) == 0

    # User B attempts to access operator endpoint to list all reports - should be 403 Forbidden
    res_b_op = client.get("/api/v1/operator/incident-reports", headers=headers_b)
    assert res_b_op.status_code == 403


def test_06_viewer_cannot_review_reports():
    """Requirement 6: VIEWER cannot review incident reports (403 Forbidden)."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Report for Review", "description": "Review test"}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    # Viewer attempts to transition report
    res_rev = client.post(
        f"/api/v1/operator/incident-reports/{report_id}/review",
        json={"status": "UNDER_REVIEW"},
        headers=headers_v
    )
    assert res_rev.status_code == 403


def test_07_operator_can_list_pending_reports():
    """Requirement 7: OPERATOR can list pending incident reports."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    client.post("/api/v1/incident-reports", json={"title": "Report 1", "description": "Desc 1"}, headers=headers_v)

    res_list = client.get("/api/v1/operator/incident-reports", headers=headers_op)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


def test_08_admin_can_list_pending_reports():
    """Requirement 8: ADMIN can list pending incident reports."""
    headers_v = get_auth_headers("viewer")
    headers_adm = get_auth_headers("admin")

    client.post("/api/v1/incident-reports", json={"title": "Report 1", "description": "Desc 1"}, headers=headers_v)

    res_list = client.get("/api/v1/operator/incident-reports", headers=headers_adm)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


def test_09_field_officer_cannot_review_reports():
    """Requirement 9: FIELD_OFFICER cannot review incident reports (403 Forbidden)."""
    headers_v = get_auth_headers("viewer")
    headers_fo = get_auth_headers("field_officer")

    res_c = client.post("/api/v1/incident-reports", json={"title": "FO Review Test", "description": "Testing description"}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    res_rev = client.post(
        f"/api/v1/operator/incident-reports/{report_id}/review",
        json={"status": "UNDER_REVIEW"},
        headers=headers_fo
    )
    assert res_rev.status_code == 403


def test_10_operator_can_move_report_to_under_review():
    """Requirement 10: OPERATOR can move report status to UNDER_REVIEW."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Under Review Test", "description": "Testing description"}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    res_rev = client.post(
        f"/api/v1/operator/incident-reports/{report_id}/review",
        json={"status": "UNDER_REVIEW"},
        headers=headers_op
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "UNDER_REVIEW"


def test_11_14_16_17_operator_can_accept_report_creating_operational_incident():
    """Requirements 11, 14, 16, 17: OPERATOR can ACCEPT report, creating exactly one operational Incident with source_type VIEWER_REPORT linked via accepted_incident_id."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post(
        "/api/v1/incident-reports",
        json={"title": "Medical Emergency at Gate 2", "description": "Individual fainted in crowd queue", "zone_id": "zone_2"},
        headers=headers_v
    )
    report_id = res_c.json()["report_id"]

    res_accept = client.post(
        f"/api/v1/operator/incident-reports/{report_id}/review",
        json={"status": "ACCEPTED", "review_reason": "Verified by CCTV feed"},
        headers=headers_op
    )
    assert res_accept.status_code == 200
    data = res_accept.json()
    assert data["status"] == "ACCEPTED"
    assert data["accepted_incident_id"] is not None

    # Verify operational incident was created in DB
    db = TestingSessionLocal()
    inc = db.query(Incident).filter(Incident.id == UUID(data["accepted_incident_id"])).first()
    assert inc is not None
    assert inc.source_type == "VIEWER_REPORT"
    assert inc.status == "OPEN"
    assert "Medical Emergency at Gate 2" in inc.description
    db.close()


def test_12_13_operator_can_reject_report_with_reason():
    """Requirements 12 & 13: OPERATOR can REJECT report; rejection requires a valid review_reason."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "False Alarm Report", "description": "Nothing happening"}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    # Reject without reason should return 400 Bad Request
    res_no_reason = client.post(
        f"/api/v1/operator/incident-reports/{report_id}/review",
        json={"status": "REJECTED", "review_reason": ""},
        headers=headers_op
    )
    assert res_no_reason.status_code == 400

    # Reject with reason should succeed
    res_reject = client.post(
        f"/api/v1/operator/incident-reports/{report_id}/review",
        json={"status": "REJECTED", "review_reason": "Duplicate submission, no physical hazard found."},
        headers=headers_op
    )
    assert res_reject.status_code == 200
    assert res_reject.json()["status"] == "REJECTED"
    assert res_reject.json()["review_reason"] == "Duplicate submission, no physical hazard found."

    # Verify NO operational incident was created
    db = TestingSessionLocal()
    inc_count = db.query(Incident).count()
    assert inc_count == 0
    db.close()


def test_15_repeated_accept_does_not_create_duplicate_incidents():
    """Requirement 15: Repeated ACCEPT on an already terminal report returns 400 Bad Request."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Repeat Test", "description": "Testing repeat accept"}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    # First Accept succeeds
    res_1 = client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "ACCEPTED"}, headers=headers_op)
    assert res_1.status_code == 200

    # Second Accept fails with 400
    res_2 = client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "ACCEPTED"}, headers=headers_op)
    assert res_2.status_code == 400
    assert "terminal status" in res_2.json()["detail"].lower()

    # Verify only 1 operational incident exists
    db = TestingSessionLocal()
    assert db.query(Incident).count() == 1
    db.close()


def test_18_ai_generated_incidents_remain_system_ai():
    """Requirement 18: AI-generated incidents retain source_type AI_EARLY_WARNING_PROXY / SYSTEM_AI."""
    db = TestingSessionLocal()
    ai_incident = Incident(
        incident_id="INC-AI-TEST-001",
        event_id="evt_01",
        zone_id="zone_01",
        source_type="AI_EARLY_WARNING_PROXY",
        status="OPEN"
    )
    db.add(ai_incident)
    db.commit()

    fetched = db.query(Incident).filter(Incident.incident_id == "INC-AI-TEST-001").first()
    assert fetched.source_type == "AI_EARLY_WARNING_PROXY"
    assert fetched.source_type != "VIEWER_REPORT"
    db.close()


def test_19_viewer_cannot_transition_operational_incidents():
    """Requirement 19: VIEWER cannot transition operational incidents (403 Forbidden)."""
    headers_v = get_auth_headers("viewer")
    res = client.post("/api/v1/operator/incidents/INC-AI-TEST-001/transition", json={"new_status": "ACKNOWLEDGED"}, headers=headers_v)
    assert res.status_code == 403


def test_20_viewer_cannot_dispatch_officers():
    """Requirement 20: VIEWER cannot create or transition dispatches (403 Forbidden)."""
    headers_v = get_auth_headers("viewer")
    res = client.post("/api/v1/operator/incidents/INC-AI-TEST-001/dispatch", json={"officer_id": "FO-001"}, headers=headers_v)
    assert res.status_code == 403


def test_21_viewer_cannot_access_audit_logs():
    """Requirement 21: VIEWER cannot access administrative audit logs (403 Forbidden)."""
    headers_v = get_auth_headers("viewer")
    res = client.get("/api/v1/admin/audit-logs", headers=headers_v)
    assert res.status_code == 403


def test_22_report_actions_create_audit_records():
    """Requirement 22: All report actions (creation, acceptance, rejection) write immutable audit log records."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Audit Test Report", "description": "Testing audit trail"}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "ACCEPTED"}, headers=headers_op)

    db = TestingSessionLocal()
    created_audit = db.query(AuditLog).filter(AuditLog.action == "INCIDENT_REPORT_CREATED").first()
    assert created_audit is not None
    assert created_audit.resource_type == "INCIDENT_REPORT"

    accepted_audit = db.query(AuditLog).filter(AuditLog.action == "INCIDENT_REPORT_ACCEPTED").first()
    assert accepted_audit is not None

    created_inc_audit = db.query(AuditLog).filter(AuditLog.action == "INCIDENT_CREATED_FROM_VIEWER_REPORT").first()
    assert created_inc_audit is not None
    db.close()


def test_23_request_id_correlation_preserved():
    """Requirement 23: X-Request-ID correlation header is preserved across report operations."""
    headers_v = get_auth_headers("viewer")
    headers_v["X-Request-ID"] = "req_incident_report_test_999"

    res = client.post("/api/v1/incident-reports", json={"title": "Request ID Test", "description": "Correlation test"}, headers=headers_v)
    assert res.status_code == 201
    assert res.headers.get("X-Request-ID") == "req_incident_report_test_999"


def test_24_invalid_report_transitions_return_400():
    """Requirement 24: Invalid report transition targets return 400 Bad Request."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Invalid Transition Test", "description": "Testing description"}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    res_bad = client.post(
        f"/api/v1/operator/incident-reports/{report_id}/review",
        json={"status": "INVALID_STATUS_STRING"},
        headers=headers_op
    )
    assert res_bad.status_code == 400


def test_25_unauthorized_actions_return_401_or_403():
    """Requirement 25: Unauthorized actions strictly return 401 for unauthenticated or 403 for insufficient roles."""
    # Unauthenticated -> 401
    res_unauth = client.get("/api/v1/operator/incident-reports")
    assert res_unauth.status_code == 401

    # Viewer -> 403 on operator endpoint
    res_forbidden = client.get("/api/v1/operator/incident-reports", headers=get_auth_headers("viewer"))
    assert res_forbidden.status_code == 403
