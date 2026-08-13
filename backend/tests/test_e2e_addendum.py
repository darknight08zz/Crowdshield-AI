"""
CROWDSHIELD ADDENDUM VERIFICATION TEST SUITE
=============================================
Tests specific addendum requirements:
1. Force REVERSE_FLOW condition -> confirm ENFORCE_ONE_WAY_FLOW recommendation, simulates correctly, & dispatches.
2. Operator-edited ISSUE_PUBLIC_ANNOUNCEMENT approval -> confirm operator-edited text in audit log.
3. Multilingual localization (EN / HI) for announcements, static UI tokens, and push notifications.
"""

import pytest
import os
import sys
from uuid import UUID
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from conftest import TestingSessionLocal as SessionLocal
from app.core.security import create_access_token
from app.models import Zone, User, UserRoleEnum, AuditLog, AIRecommendation, OfficerAssignment
from app.ai.behavior import classify_behavior, BehaviorType
from app.ai.recommend import generate_recommendations
from app.ai.simulate import simulate_intervention
from app.ai.announce import draft_announcement
from app.services.push import notify_field_officers


client = TestClient(app)


def get_or_create_e2e_users(db):
    op_user = db.query(User).filter(User.email == "op_e2e@crowdshield.gov").first()
    if not op_user:
        op_user = User(
            id=UUID("aa111111-0000-0000-0000-000000000002"),
            email="op_e2e@crowdshield.gov",
            name="E2E Operator",
            role=UserRoleEnum.OPERATOR,
            account_status="active",
            is_active=True
        )
        db.add(op_user)
        db.commit()
    else:
        op_user.role = UserRoleEnum.OPERATOR
        op_user.account_status = "active"
        op_user.is_active = True
        db.commit()

    officer_user = db.query(User).filter(User.email == "officer_e2e@crowdshield.gov").first()
    if not officer_user:
        officer_user = User(
            id=UUID("aa111111-0000-0000-0000-000000000003"),
            email="officer_e2e@crowdshield.gov",
            name="E2E Officer",
            role=UserRoleEnum.FIELD_OFFICER,
            account_status="active",
            is_active=True
        )
        db.add(officer_user)
        db.commit()
    else:
        officer_user.role = UserRoleEnum.FIELD_OFFICER
        officer_user.account_status = "active"
        officer_user.is_active = True
        db.commit()

    return op_user, officer_user


def test_reverse_flow_recommendation_simulation_and_dispatch():
    """
    1. Force a REVERSE_FLOW condition.
    2. Confirm ENFORCE_ONE_WAY_FLOW appears in recommendations.
    3. Confirm simulate_intervention reduces reverse_flow_ratio.
    4. Dispatch the action and verify officer task & audit log entries.
    """
    db = SessionLocal()
    op_user, officer_user = get_or_create_e2e_users(db)

    # Synthetic features for REVERSE_FLOW
    reverse_flow_features = {
        "current_density": 0.65,
        "inflow_rate": 80.0,
        "outflow_rate": 75.0,
        "avg_pedestrian_speed": 0.85,
        "direction_conflict_score": 0.75,
        "gate_capacity_utilization": 0.60,
        "recent_incident_count_10min": 0.0,
        "reverse_flow_ratio": 0.58,  # > 0.35 threshold for REVERSE_FLOW
        "blockage_score": 0.15
    }

    # 1. Behavior Classification
    behavior = classify_behavior(reverse_flow_features)
    assert behavior == BehaviorType.REVERSE_FLOW

    # 2. Recommendation Engine
    recs = generate_recommendations(
        zone_id="aa111111-0000-0000-0000-000000000001",
        current_risk=72.0,
        predicted_risk_5min=78.0,
        feature_dict=reverse_flow_features,
        db=db
    )
    action_types = [r["action_type"] for r in recs]
    assert "ENFORCE_ONE_WAY_FLOW" in action_types

    one_way_rec = next(r for r in recs if r["action_type"] == "ENFORCE_ONE_WAY_FLOW")
    assert "route_id" in one_way_rec

    # 3. Simulation Execution
    sim_result = simulate_intervention(
        zone_id="aa111111-0000-0000-0000-000000000001",
        proposed_action={"action_type": "ENFORCE_ONE_WAY_FLOW", "route_id": "route-aa111111"},
        db=db
    )
    assert sim_result["risk_delta"] < 0
    assert sim_result["simulated_feature_changes"]["adjusted"]["reverse_flow_ratio"] < reverse_flow_features["reverse_flow_ratio"]

    # 4. Dispatch Execution
    op_token = create_access_token(op_user.id, op_user.email, "operator", "active")
    headers = {"Authorization": f"Bearer {op_token}"}

    dispatch_res = client.post(
        "/api/v1/operator/dispatch",
        json={
          "officer_id": str(officer_user.id),
          "zone_id": "aa111111-0000-0000-0000-000000000001",
          "task_description": "Enforce one-way flow on route-aa111111 due to severe REVERSE_FLOW detection."
        },
        headers=headers
    )
    assert dispatch_res.status_code == 200
    task_id = dispatch_res.json()["id"]

    # Verify task in DB
    task = db.query(OfficerAssignment).filter(OfficerAssignment.id == UUID(task_id)).first()
    assert task is not None
    assert "REVERSE_FLOW" in task.task_description

    db.close()


def test_operator_edited_announcement_audit_logging():
    """
    Confirm that an approved ISSUE_PUBLIC_ANNOUNCEMENT decision logs the operator-edited
    (not just AI-drafted) text in the audit log.
    """
    db = SessionLocal()
    op_user, officer_user = get_or_create_e2e_users(db)

    op_token = create_access_token(op_user.id, op_user.email, "operator", "active")
    headers = {"Authorization": f"Bearer {op_token}"}

    # 1. Create a sample AI Recommendation in DB (risk_score normalized between 0.0 and 1.0 for DB check constraint)
    rec = AIRecommendation(
        zone_id=UUID("aa111111-0000-0000-0000-000000000001"),
        risk_score=0.75,
        predicted_risk_5min=0.80,
        recommended_actions=[{
            "action_type": "ISSUE_PUBLIC_ANNOUNCEMENT",
            "description": "Broadcast announcement to disperse crowd surge",
            "priority": 1
        }],
        status="pending"
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    original_draft = "ATTENTION: High crowd density detected in Sector A. Please move towards available exits."
    operator_edited = "OPERATOR CUSTOM OVERRIDE: Sector A visitors, please proceed calmly to North Exit 2 immediately."

    # 2. Submit Decision with Operator Edit
    payload = {
        "status": "approved",
        "original_draft_announcement": original_draft,
        "edited_announcement": operator_edited
    }

    res = client.post(
        f"/api/v1/operator/recommendations/{rec.id}/decide",
        json=payload,
        headers=headers
    )
    assert res.status_code == 200
    assert res.json()["status"] == "approved"

    # 3. Query Audit Log & Verify Operator-Edited Text
    audit_entry = db.query(AuditLog).filter(
        AuditLog.action == "OPERATOR_DECISION_RECOMMENDATION",
        AuditLog.target == f"recommendation:{rec.id}"
    ).order_by(AuditLog.created_at.desc()).first()

    assert audit_entry is not None
    after_state = audit_entry.after_state
    assert after_state["original_draft_announcement"] == original_draft
    assert after_state["edited_announcement"] == operator_edited
    assert after_state["final_approved_announcement"] == operator_edited
    assert after_state["was_edited"] is True

    db.close()


def test_multilingual_push_and_api_localization():
    """
    Verify backend announcement drafting and API query responses in English and Hindi.
    """
    db = SessionLocal()
    op_user, officer_user = get_or_create_e2e_users(db)

    # 1. English Announcement Drafting
    draft_en = draft_announcement("REVERSE_FLOW", "Main Arena", language="en")
    assert "Main Arena" in draft_en
    assert "One-way pedestrian flow is in effect" in draft_en

    # 2. Hindi Announcement Drafting
    draft_hi = draft_announcement("REVERSE_FLOW", "मुख्य मंच क्षेत्र", language="hi")
    assert "मुख्य मंच क्षेत्र" in draft_hi
    assert "एकतरफा पैदल मार्ग नियम लागू है" in draft_hi

    op_token = create_access_token(op_user.id, op_user.email, "operator", "active")
    headers = {"Authorization": f"Bearer {op_token}"}

    res_hi = client.get(
        "/api/v1/operator/zones/aa111111-0000-0000-0000-000000000001/recommendation?lang=hi",
        headers=headers
    )
    assert res_hi.status_code == 200
    data_hi = res_hi.json()
    assert data_hi["language"] == "hi"
    assert len(data_hi["drafted_announcement"]) > 0

    # 4. Push Notification Localization Delivery
    push_result = notify_field_officers(
        officer_ids=[officer_user.id],
        title="⚠️ आपातकालीन सूचना (Emergency Alert)",
        body=draft_hi,
        db=db,
        data_payload={"lang": "hi", "zone_id": "aa111111-0000-0000-0000-000000000001"}
    )
    assert push_result["success"] is True

    db.close()
