"""
CROWDSHIELD PHASE 3 REALTIME & NOTIFICATION TEST SUITE
=====================================================
Tests device token registration, Supabase Realtime channel configurations,
and dispatch execution workflows (alerts, officer assignments, push triggers).
"""

import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import Event, Zone, Gate, User, UserRoleEnum, AIRecommendation, RecommendationStatusEnum, DeviceToken, Alert, OfficerAssignment, AuditLog
from app.services.realtime import get_web_control_room_channels, get_citizen_app_channels, get_field_officer_channels
from app.services.push import send_fcm_multicast, notify_zone_citizens, notify_field_officers
from app.services.dispatch import dispatch_approved_action


# In-memory SQLite setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def phase3_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Seed test entities
    event_id = uuid.uuid4()
    zone_id = uuid.uuid4()
    gate_id = uuid.uuid4()
    citizen_user_id = uuid.uuid4()
    officer_user_id = uuid.uuid4()
    rec_id = uuid.uuid4()

    event = Event(id=event_id, name="Phase 3 Test Event", date=datetime.utcnow(), venue="Stadium", status="active")
    zone = Zone(id=zone_id, event_id=event_id, name="Test Bottleneck Zone", capacity=3000, current_density=0.85, risk_score=0.80)
    gate = Gate(id=gate_id, event_id=event_id, zone_id=zone_id, name="Emergency Gate 1", type="emergency", capacity_per_min=250, status="closed")

    citizen = User(id=citizen_user_id, role=UserRoleEnum.CITIZEN.value, name="Test Citizen", email="citizen@test.com")
    officer = User(id=officer_user_id, role=UserRoleEnum.FIELD_OFFICER.value, name="Test Officer", email="officer@test.com")

    # Add Device Tokens
    citizen_token = DeviceToken(user_id=citizen_user_id, fcm_token="fcm_token_citizen_123", platform="android")
    officer_token = DeviceToken(user_id=officer_user_id, fcm_token="fcm_token_officer_456", platform="android")

    # Add AI Recommendation
    rec = AIRecommendation(
        id=rec_id,
        zone_id=zone_id,
        risk_score=82.0,
        predicted_risk_5min=90.0,
        recommended_actions=[
            {"action_type": "OPEN_EMERGENCY_GATE", "target_gate_id": str(gate_id)},
            {"action_type": "DISPATCH_FIELD_OFFICERS", "recommended_officer_count": 1},
            {"action_type": "ISSUE_CITIZEN_REROUTE_ALERT"}
        ],
        status=RecommendationStatusEnum.PENDING.value
    )

    db.add(event)
    db.add(zone)
    db.add(gate)
    db.add(citizen)
    db.add(officer)
    db.add(citizen_token)
    db.add(officer_token)
    db.add(rec)
    db.commit()

    yield db, rec_id, zone_id, officer_user_id

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_realtime_channels():
    event_id = uuid.uuid4()
    zone_id = uuid.uuid4()

    web_channels = get_web_control_room_channels(event_id)
    assert len(web_channels) == 4

    citizen_channels = get_citizen_app_channels(event_id, zone_id)
    assert len(citizen_channels) == 2

    officer_channels = get_field_officer_channels(uuid.uuid4())
    assert len(officer_channels) == 1


def test_mock_push_notifications(phase3_db):
    db, rec_id, zone_id, officer_id = phase3_db

    # Test direct multicast push
    res1 = send_fcm_multicast(tokens=["fake_token"], title="Test", body="Body")
    assert res1["status"] == "MOCK"
    assert res1["success"] is False
    assert res1["requested_count"] == 1

    # Test zone citizen push
    res2 = notify_zone_citizens(zone_id=zone_id, title="Alert", body="Test Advisory", db=db)
    assert res2["requested_count"] > 0

    # Test officer push
    res3 = notify_field_officers(officer_ids=[officer_id], title="Task", body="New Assignment", db=db)
    assert res3["requested_count"] > 0



def test_dispatch_approved_action_workflow(phase3_db):
    db, rec_id, zone_id, officer_id = phase3_db

    dispatch_res = dispatch_approved_action(recommendation_id=rec_id, db=db)

    assert dispatch_res["recommendation_id"] == str(rec_id)
    assert len(dispatch_res["actions_executed"]) >= 3
    assert dispatch_res["dispatched_officers_count"] > 0

    # Verify Gate status updated to 'open'
    gate = db.query(Gate).filter(Gate.zone_id == zone_id).first()
    assert gate.status == "open"

    # Verify Alert row created
    alert = db.query(Alert).filter(Alert.zone_id == zone_id).first()
    assert alert is not None
    assert "SAFETY ADVISORY" in alert.message

    # Verify OfficerAssignment created
    assignment = db.query(OfficerAssignment).filter(OfficerAssignment.zone_id == zone_id).first()
    assert assignment is not None

    # Verify AuditLog created
    audit = db.query(AuditLog).filter(AuditLog.action == "EXECUTE_APPROVED_DISPATCH").first()
    assert audit is not None
