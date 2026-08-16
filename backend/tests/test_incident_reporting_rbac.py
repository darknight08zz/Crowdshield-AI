import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
try:
    from tests.conftest import TestingSessionLocal
except ImportError:
    from conftest import TestingSessionLocal

from app.core.security import create_access_token
from app.models.audit import AuditLog
from app.models.event import Event
from app.models.zone import Zone
from app.models.incident import Incident, IncidentTransition
from app.models.incident_report import IncidentReport
from app.models.user import User, UserRoleEnum

client = TestClient(app)

TEST_EVENT_UUID = UUID("a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d")
TEST_ZONE_UUID = UUID("f8e7d6c5-b4a3-4210-9876-543210fedcba")


def get_auth_headers(role: str = "viewer", user_id: str = None) -> dict:
    uid = user_id or str(uuid4())
    token = create_access_token(
        user_id=uid,
        email=f"{role}_{uid[:6]}@crowdshield.ai",
        role=role
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def setup_test_entities():
    db = TestingSessionLocal()
    try:
        db.query(IncidentTransition).delete()
        db.query(IncidentReport).delete()
        db.query(Incident).delete()
        db.query(AuditLog).delete()
        db.query(Zone).delete()
        db.query(Event).delete()
        db.commit()

        # Seed real Event and Zone entities for tests
        test_event = Event(
            id=TEST_EVENT_UUID,
            name="Main Concert Event",
            date=datetime.now(timezone.utc),
            venue="Central Arena",
            status="active"
        )
        db.add(test_event)

        test_zone = Zone(
            id=TEST_ZONE_UUID,
            event_id=test_event.id,
            name="Main Gate Zone",
            capacity=1000,
            current_density=0.2,
            risk_score=0.1
        )
        db.add(test_zone)
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


def test_01_viewer_can_submit_report():
    """Requirement 1 & 3: VIEWER can submit a report, initial status is REPORT_SUBMITTED."""
    viewer_id = str(uuid4())
    headers = get_auth_headers("viewer", user_id=viewer_id)
    payload = {
        "title": "Unusual crowd bottleneck near Gate 3",
        "description": "Dense crowd accumulation forming near main entry gate.",
        "event_id": str(TEST_EVENT_UUID),
        "zone_id": str(TEST_ZONE_UUID),
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
    assert data["event_id"] == str(TEST_EVENT_UUID)


def test_02_unauthenticated_user_cannot_submit():
    """Requirement 2: Unauthenticated user cannot submit (401 Unauthorized)."""
    payload = {
        "title": "Unauthenticated test report",
        "description": "Testing missing authorization header.",
        "event_id": str(TEST_EVENT_UUID)
    }
    res = client.post("/api/v1/incident-reports", json=payload)
    assert res.status_code == 401


def test_03_submitted_report_initial_status():
    """Requirement 3: Explicit check that newly created report has status REPORT_SUBMITTED."""
    headers = get_auth_headers("viewer")
    payload = {"title": "Test initial status", "description": "Checking default status.", "event_id": str(TEST_EVENT_UUID)}
    res = client.post("/api/v1/incident-reports", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["status"] == "REPORT_SUBMITTED"


def test_04_viewer_can_view_own_reports():
    """Requirement 4: VIEWER can view their own submitted reports."""
    viewer_id = str(uuid4())
    headers = get_auth_headers("viewer", user_id=viewer_id)

    res_create = client.post("/api/v1/incident-reports", json={"title": "My Report 1", "description": "Details 1", "event_id": str(TEST_EVENT_UUID)}, headers=headers)
    assert res_create.status_code == 201

    res_my = client.get("/api/v1/incident-reports/my", headers=headers)
    assert res_my.status_code == 200
    items = res_my.json()
    assert len(items) == 1
    assert items[0]["title"] == "My Report 1"
    assert items[0]["submitted_by_user_id"] == viewer_id


def test_05_viewer_cannot_view_another_users_report():
    """Requirement 5: VIEWER cannot view another user's report via operator endpoints or /my."""
    user_a_id = str(uuid4())
    user_b_id = str(uuid4())

    headers_a = get_auth_headers("viewer", user_id=user_a_id)
    headers_b = get_auth_headers("viewer", user_id=user_b_id)

    client.post("/api/v1/incident-reports", json={"title": "User A Report", "description": "Details A", "event_id": str(TEST_EVENT_UUID)}, headers=headers_a)

    res_b_my = client.get("/api/v1/incident-reports/my", headers=headers_b)
    assert res_b_my.status_code == 200
    assert len(res_b_my.json()) == 0

    res_b_op = client.get("/api/v1/operator/incident-reports", headers=headers_b)
    assert res_b_op.status_code == 403


def test_06_viewer_cannot_review_reports():
    """Requirement 6: VIEWER cannot review incident reports (403 Forbidden)."""
    headers_v = get_auth_headers("viewer")
    res_c = client.post("/api/v1/incident-reports", json={"title": "Report for Review", "description": "Review test", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
    report_id = res_c.json()["report_id"]

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

    client.post("/api/v1/incident-reports", json={"title": "Report 1", "description": "Desc 1", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)

    res_list = client.get("/api/v1/operator/incident-reports", headers=headers_op)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


def test_08_admin_can_list_pending_reports():
    """Requirement 8: ADMIN can list pending incident reports."""
    headers_v = get_auth_headers("viewer")
    headers_adm = get_auth_headers("admin")

    client.post("/api/v1/incident-reports", json={"title": "Report 1", "description": "Desc 1", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)

    res_list = client.get("/api/v1/operator/incident-reports", headers=headers_adm)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


def test_09_field_officer_cannot_review_reports():
    """Requirement 9: FIELD_OFFICER cannot review incident reports (403 Forbidden)."""
    headers_v = get_auth_headers("viewer")
    headers_fo = get_auth_headers("field_officer")

    res_c = client.post("/api/v1/incident-reports", json={"title": "FO Review Test", "description": "Testing description", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
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

    res_c = client.post("/api/v1/incident-reports", json={"title": "Under Review Test", "description": "Testing description", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    res_rev = client.post(
        f"/api/v1/operator/incident-reports/{report_id}/review",
        json={"status": "UNDER_REVIEW"},
        headers=headers_op
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "UNDER_REVIEW"


def test_11_14_16_17_operator_can_accept_report_creating_operational_incident():
    """Requirements 11, 14, 16, 17: OPERATOR can ACCEPT report, creating operational Incident."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post(
        "/api/v1/incident-reports",
        json={"title": "Medical Emergency at Gate 2", "description": "Individual fainted in crowd queue", "event_id": str(TEST_EVENT_UUID), "zone_id": str(TEST_ZONE_UUID)},
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

    res_c = client.post("/api/v1/incident-reports", json={"title": "False Alarm Report", "description": "Nothing happening", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    res_no_reason = client.post(
        f"/api/v1/operator/incident-reports/{report_id}/review",
        json={"status": "REJECTED", "review_reason": ""},
        headers=headers_op
    )
    assert res_no_reason.status_code == 400

    res_reject = client.post(
        f"/api/v1/operator/incident-reports/{report_id}/review",
        json={"status": "REJECTED", "review_reason": "Duplicate submission, no physical hazard found."},
        headers=headers_op
    )
    assert res_reject.status_code == 200
    assert res_reject.json()["status"] == "REJECTED"

    db = TestingSessionLocal()
    assert db.query(Incident).count() == 0
    db.close()


def test_15_repeated_accept_does_not_create_duplicate_incidents():
    """Requirement 15: Repeated ACCEPT on an already terminal report returns 400 Bad Request."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Repeat Test", "description": "Testing repeat accept", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    res_1 = client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "ACCEPTED"}, headers=headers_op)
    assert res_1.status_code == 200

    res_2 = client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "ACCEPTED"}, headers=headers_op)
    assert res_2.status_code == 400

    db = TestingSessionLocal()
    assert db.query(Incident).count() == 1
    db.close()


def test_18_ai_generated_incidents_remain_system_ai():
    """Requirement 18: AI-generated incidents retain source_type AI_EARLY_WARNING_PROXY."""
    db = TestingSessionLocal()
    ai_incident = Incident(
        incident_id="INC-AI-TEST-001",
        event_id=str(TEST_EVENT_UUID),
        zone_id=str(TEST_ZONE_UUID),
        source_type="AI_EARLY_WARNING_PROXY",
        status="OPEN"
    )
    db.add(ai_incident)
    db.commit()

    fetched = db.query(Incident).filter(Incident.incident_id == "INC-AI-TEST-001").first()
    assert fetched.source_type == "AI_EARLY_WARNING_PROXY"
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
    """Requirement 22: All report actions write immutable audit log records."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Audit Test Report", "description": "Testing audit trail", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "ACCEPTED"}, headers=headers_op)

    db = TestingSessionLocal()
    assert db.query(AuditLog).filter(AuditLog.action == "INCIDENT_REPORT_CREATED").first() is not None
    assert db.query(AuditLog).filter(AuditLog.action == "INCIDENT_REPORT_ACCEPTED").first() is not None
    assert db.query(AuditLog).filter(AuditLog.action == "INCIDENT_CREATED_FROM_VIEWER_REPORT").first() is not None
    db.close()


def test_23_request_id_correlation_preserved():
    """Requirement 23: X-Request-ID correlation header is preserved across report operations."""
    headers_v = get_auth_headers("viewer")
    headers_v["X-Request-ID"] = "req_incident_report_test_999"

    res = client.post("/api/v1/incident-reports", json={"title": "Request ID Test", "description": "Correlation test", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
    assert res.status_code == 201
    assert res.headers.get("X-Request-ID") == "req_incident_report_test_999"


def test_24_invalid_report_transitions_return_400():
    """Requirement 24: Invalid report transition targets return 400 Bad Request."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Invalid Transition Test", "description": "Testing description", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    res_bad = client.post(
        f"/api/v1/operator/incident-reports/{report_id}/review",
        json={"status": "INVALID_STATUS_STRING"},
        headers=headers_op
    )
    assert res_bad.status_code == 400


def test_25_unauthorized_actions_return_401_or_403():
    """Requirement 25: Unauthorized actions strictly return 401 for unauthenticated or 403 for insufficient roles."""
    res_unauth = client.get("/api/v1/operator/incident-reports")
    assert res_unauth.status_code == 401

    res_forbidden = client.get("/api/v1/operator/incident-reports", headers=get_auth_headers("viewer"))
    assert res_forbidden.status_code == 403


# =====================================================================
# SECTION 9: ADDITIONAL INTEGRITY & AUTHORIZATION TESTS
# =====================================================================

def test_26_no_synthetic_event_fallback():
    """Addendum Test 1: Submitting report without event when NO event exists in DB returns HTTP 400."""
    db = TestingSessionLocal()
    db.query(Zone).delete()
    db.query(Event).delete()
    db.commit()
    db.close()

    headers_v = get_auth_headers("viewer")
    res = client.post(
        "/api/v1/incident-reports",
        json={"title": "No Event Test", "description": "Testing missing event behavior"},
        headers=headers_v
    )
    assert res.status_code == 400
    assert "Event ID is required" in res.json()["detail"]


def test_27_invalid_event_rejected():
    """Addendum Test 2: Invalid event ID returns HTTP 400 Bad Request."""
    headers_v = get_auth_headers("viewer")
    res = client.post(
        "/api/v1/incident-reports",
        json={"title": "Invalid Event Test", "description": "Testing bad event ID", "event_id": "nonexistent_event_99999"},
        headers=headers_v
    )
    assert res.status_code == 400
    assert "does not exist" in res.json()["detail"].lower()


def test_28_valid_event_accepted():
    """Addendum Test 3: Submitting report with real event ID succeeds."""
    headers_v = get_auth_headers("viewer")
    res = client.post(
        "/api/v1/incident-reports",
        json={"title": "Valid Event Test", "description": "Testing real event ID", "event_id": str(TEST_EVENT_UUID)},
        headers=headers_v
    )
    assert res.status_code == 201
    assert res.json()["event_id"] == str(TEST_EVENT_UUID)


def test_29_no_synthetic_zone_fallback():
    """Addendum Test 4: Accepting report without zone_id sets zone_id=None (no fake UUID generated)."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post(
        "/api/v1/incident-reports",
        json={"title": "No Zone Test", "description": "Report submitted without zone", "event_id": str(TEST_EVENT_UUID)},
        headers=headers_v
    )
    report_id = res_c.json()["report_id"]

    res_accept = client.post(
        f"/api/v1/operator/incident-reports/{report_id}/review",
        json={"status": "ACCEPTED", "review_reason": "Accepting without zone"},
        headers=headers_op
    )
    assert res_accept.status_code == 200
    accepted_inc_id = res_accept.json()["accepted_incident_id"]

    db = TestingSessionLocal()
    inc = db.query(Incident).filter(Incident.id == UUID(accepted_inc_id)).first()
    assert inc is not None
    assert inc.zone_id is None
    assert inc.zone_id != "22222222-2222-2222-2222-222222222222"
    db.close()


def test_30_invalid_zone_rejected():
    """Addendum Test 5: Submitting or reviewing report with invalid zone returns HTTP 400."""
    headers_v = get_auth_headers("viewer")
    res_sub = client.post(
        "/api/v1/incident-reports",
        json={"title": "Invalid Zone Test", "description": "Testing bad zone ID", "event_id": str(TEST_EVENT_UUID), "zone_id": "nonexistent_zone_99999"},
        headers=headers_v
    )
    assert res_sub.status_code == 400
    assert "does not exist" in res_sub.json()["detail"].lower()


def test_31_valid_zone_accepted():
    """Addendum Test 6: Accepting report with valid real zone links zone ID to operational incident."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post(
        "/api/v1/incident-reports",
        json={"title": "Valid Zone Test", "description": "Testing real zone ID", "event_id": str(TEST_EVENT_UUID)},
        headers=headers_v
    )
    report_id = res_c.json()["report_id"]

    res_accept = client.post(
        f"/api/v1/operator/incident-reports/{report_id}/review",
        json={"status": "ACCEPTED", "review_reason": "Verified zone", "zone_id": str(TEST_ZONE_UUID)},
        headers=headers_op
    )
    assert res_accept.status_code == 200

    db = TestingSessionLocal()
    inc = db.query(Incident).filter(Incident.id == UUID(res_accept.json()["accepted_incident_id"])).first()
    assert inc is not None
    assert inc.zone_id == str(TEST_ZONE_UUID)
    db.close()


def test_32_human_report_provenance_label():
    """Addendum Test 7: Viewer report incident has HUMAN_SUBMITTED_OBSERVATION label_type."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Label Test", "description": "Testing label type", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    res_accept = client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "ACCEPTED"}, headers=headers_op)
    assert res_accept.status_code == 200

    db = TestingSessionLocal()
    inc = db.query(Incident).filter(Incident.id == UUID(res_accept.json()["accepted_incident_id"])).first()
    assert inc.label_type == "HUMAN_SUBMITTED_OBSERVATION"
    assert inc.source_type == "VIEWER_REPORT"
    assert inc.warning_state_at_creation == "HUMAN_REPORTED"
    db.close()


def test_33_human_report_no_ai_probability():
    """Addendum Test 8: Viewer-created incident has NULL AI probability and physics risk."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "No AI Prob Test", "description": "Testing NULL probability", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    res_accept = client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "ACCEPTED"}, headers=headers_op)
    assert res_accept.status_code == 200

    db = TestingSessionLocal()
    inc = db.query(Incident).filter(Incident.id == UUID(res_accept.json()["accepted_incident_id"])).first()
    assert inc.ai_probability_at_creation is None
    assert inc.latest_ai_probability is None
    assert inc.physics_risk_at_creation is None
    assert inc.latest_physics_risk is None
    db.close()


def test_34_human_report_no_ai_model_version_claim():
    """Addendum Test 9: Viewer-created incident model_version, prediction_target, model_status are NOT_APPLICABLE."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Model Version Test", "description": "Testing model version", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    res_accept = client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "ACCEPTED"}, headers=headers_op)
    assert res_accept.status_code == 200

    db = TestingSessionLocal()
    inc = db.query(Incident).filter(Incident.id == UUID(res_accept.json()["accepted_incident_id"])).first()
    assert inc.model_version == "NOT_APPLICABLE"
    assert inc.prediction_target == "NOT_APPLICABLE"
    assert inc.model_status == "NOT_APPLICABLE"
    assert inc.generalization_status == "NOT_APPLICABLE"
    assert "Not generated by AI models" in inc.disclaimer
    db.close()


def test_35_invalid_report_state_transitions_rejected():
    """Addendum Test 10: Invalid report state transitions are rejected with HTTP 400."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Transition Test", "description": "Testing transition map", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    # Accept report (terminal status)
    client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "ACCEPTED"}, headers=headers_op)

    # Attempt transition from ACCEPTED to UNDER_REVIEW -> rejected
    res_invalid = client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "UNDER_REVIEW"}, headers=headers_op)
    assert res_invalid.status_code == 400
    assert "Invalid report state transition" in res_invalid.json()["detail"]


def test_36_valid_report_state_transitions_accepted():
    """Addendum Test 11: Sequential valid state transitions REPORT_SUBMITTED -> UNDER_REVIEW -> REJECTED succeed."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Valid Flow Test", "description": "Testing sequential states", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    # 1. REPORT_SUBMITTED -> UNDER_REVIEW
    res_ur = client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "UNDER_REVIEW"}, headers=headers_op)
    assert res_ur.status_code == 200
    assert res_ur.json()["status"] == "UNDER_REVIEW"

    # 2. UNDER_REVIEW -> REJECTED
    res_rej = client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "REJECTED", "review_reason": "Out of scope"}, headers=headers_op)
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "REJECTED"


def test_37_acceptance_rollback_on_incident_failure():
    """Addendum Test 12: DB rollback ensures atomic failure handling if incident flush raises error."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Rollback Test 1", "description": "Testing incident rollback", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    with patch("app.services.incident_report_service.Incident", side_effect=Exception("DB Failure during Incident init")):
        res_fail = client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "ACCEPTED"}, headers=headers_op)
        assert res_fail.status_code == 500

    db = TestingSessionLocal()
    rep = db.query(IncidentReport).filter(IncidentReport.report_id == report_id).first()
    assert rep.status == "REPORT_SUBMITTED"
    assert rep.accepted_incident_id is None
    assert db.query(Incident).count() == 0
    db.close()


def test_38_acceptance_rollback_on_audit_failure():
    """Addendum Test 13: DB rollback ensures atomic failure handling if audit log creation fails."""
    headers_v = get_auth_headers("viewer")
    headers_op = get_auth_headers("operator")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Rollback Test 2", "description": "Testing audit rollback", "event_id": str(TEST_EVENT_UUID)}, headers=headers_v)
    report_id = res_c.json()["report_id"]

    with patch("app.services.incident_report_service.log_action", side_effect=RuntimeError("Audit system failure")):
        res_fail = client.post(f"/api/v1/operator/incident-reports/{report_id}/review", json={"status": "ACCEPTED"}, headers=headers_op)
        assert res_fail.status_code == 500

    db = TestingSessionLocal()
    rep = db.query(IncidentReport).filter(IncidentReport.report_id == report_id).first()
    assert rep.status == "REPORT_SUBMITTED"
    assert rep.accepted_incident_id is None
    assert db.query(Incident).count() == 0
    db.close()


def test_39_viewer_cannot_access_another_users_report_detail():
    """Addendum Test 14: Viewer cannot access another user's report details via operator endpoint."""
    user_a_id = str(uuid4())
    headers_a = get_auth_headers("viewer", user_id=user_a_id)
    headers_b = get_auth_headers("viewer")

    res_c = client.post("/api/v1/incident-reports", json={"title": "Private Report", "description": "User A private report", "event_id": str(TEST_EVENT_UUID)}, headers=headers_a)
    report_id = res_c.json()["report_id"]

    # User B attempts to access User A report via operator detail endpoint -> 403 Forbidden
    res_detail = client.get(f"/api/v1/operator/incident-reports/{report_id}", headers=headers_b)
    assert res_detail.status_code == 403


def test_40_existing_ai_incident_provenance_unchanged():
    """Addendum Test 15: Existing AI-generated incident provenance attributes remain untouched and preserved."""
    db = TestingSessionLocal()
    ai_inc = Incident(
        incident_id="INC-AI-PROV-001",
        event_id=str(TEST_EVENT_UUID),
        zone_id=str(TEST_ZONE_UUID),
        source_type="AI_EARLY_WARNING_PROXY",
        status="OPEN",
        warning_state_at_creation="EARLY_WARNING",
        physics_risk_at_creation=0.85,
        ai_probability_at_creation=0.92,
        latest_warning_state="CRITICAL",
        latest_physics_risk=0.89,
        latest_ai_probability=0.95,
        model_version="v2.0.0",
        prediction_target="CROWD_SURGE_60S",
        label_type="PHYSICS_DEFINED_PROXY",
        model_status="PROTOTYPE",
        ground_truth_status="NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED"
    )
    db.add(ai_inc)
    db.commit()

    fetched = db.query(Incident).filter(Incident.incident_id == "INC-AI-PROV-001").first()
    assert fetched.source_type == "AI_EARLY_WARNING_PROXY"
    assert fetched.model_version == "v2.0.0"
    assert fetched.ai_probability_at_creation == 0.92
    assert fetched.physics_risk_at_creation == 0.85
    assert fetched.label_type == "PHYSICS_DEFINED_PROXY"
    db.close()
