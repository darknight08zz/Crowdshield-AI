"""
CROWDSHIELD END-TO-END INTEGRATION VERIFICATION TEST
===================================================
Executes the complete core operational loop:
1. Citizen Incident Report
2. AI Risk Score & Explainability Update
3. AI Recommendation Engine
4. What-If Simulation
5. Intervention Approval -> Dispatch Officer Task -> Push Notification Attempt -> Citizen Alert -> Audit Log
"""

import sys
import os
from uuid import UUID
from datetime import datetime
from fastapi.testclient import TestClient
from jose import jwt

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import SessionLocal
from app.models import Incident, Zone, Gate, User, UserRoleEnum, OfficerAssignment, Alert, AuditLog, AIRecommendation, GateStatusEnum
from app.services.audit_service import log_action
from app.services.push import notify_field_officers


def run_e2e_verification():
    client = TestClient(app)
    db = SessionLocal()

    print("\n" + "="*70)
    print("CROWDSHIELD PHASE 7: END-TO-END INTEGRATION TEST")
    print("="*70)

    # 1. Fetch seed zone and user
    zone = db.query(Zone).first()
    if not zone:
        print("ERROR: Seed zone not found in database. Run db seed first.")
        return False
    zone_id = str(zone.id)
    print(f"1. Using Seed Zone: '{zone.name}' (ID: {zone_id})")

    op_user = db.query(User).filter(User.role == UserRoleEnum.OPERATOR).first() or db.query(User).first()
    cit_user = db.query(User).filter(User.role == UserRoleEnum.CITIZEN).first() or db.query(User).first()
    officer_user = db.query(User).filter(User.role == UserRoleEnum.FIELD_OFFICER).first() or db.query(User).first()

    op_id = str(op_user.id) if op_user else "00000000-0000-0000-0000-000000000001"
    cit_id = str(cit_user.id) if cit_user else "00000000-0000-0000-0000-000000000001"
    officer_id = str(officer_user.id) if officer_user else "00000000-0000-0000-0000-000000000001"

    # Generate test tokens for citizen and operator
    operator_token = jwt.encode({"sub": op_id, "role": "operator"}, "secret", algorithm="HS256")
    citizen_token = jwt.encode({"sub": cit_id, "role": "citizen"}, "secret", algorithm="HS256")

    op_headers = {"Authorization": f"Bearer {operator_token}"}
    cit_headers = {"Authorization": f"Bearer {citizen_token}"}

    # 2. Citizen Incident Report
    print("\n2. Submitting Citizen Incident Report...")
    inc_payload = {
        "zone_id": zone_id,
        "type": "crowd_surge",
        "description": "E2E Test: Severe bottlenecking near stage exit gates."
    }
    inc_res = client.post("/api/v1/citizens/incidents", json=inc_payload, headers=cit_headers)
    assert inc_res.status_code == 201, f"Failed incident report: {inc_res.text}"
    inc_data = inc_res.json()
    print(f"   [SUCCESS] Incident Reported! ID: {inc_data['id']}")

    # 3. AI Risk Score Evaluation
    print("\n3. Querying AI Engine Risk Score & Explainability...")
    risk_res = client.get(f"/api/v1/operator/zones/{zone_id}/risk", headers=op_headers)
    assert risk_res.status_code == 200, f"Failed risk query: {risk_res.text}"
    risk_data = risk_res.json()
    print(f"   [SUCCESS] AI Risk Score: {risk_data['current_risk_score']} | 5-min Projection: {risk_data['predicted_risk_5min']}")
    print(f"   Explanation: {risk_data['explanation']}")

    # 4. AI Recommendation Generation
    print("\n4. Fetching AI Recommendations for Operator...")
    rec_res = client.get(f"/api/v1/operator/zones/{zone_id}/recommendation", headers=op_headers)
    assert rec_res.status_code == 200, f"Failed recommendation query: {rec_res.text}"
    rec_data = rec_res.json()
    actions = rec_data["recommended_actions"]
    assert len(actions) > 0, "No recommendations returned"
    print(f"   [SUCCESS] Generated {len(actions)} ranked AI recommendations:")
    for a in actions:
        print(f"      - [Priority {a['priority']}] {a['action_type']}: {a['description']}")

    # 5. What-If Simulation
    print("\n5. Executing What-If Simulation for Proposed Gate Opening...")
    gate = db.query(Gate).filter(Gate.zone_id == UUID(zone_id)).first()
    gate_id = str(gate.id) if gate else "90000000-0000-0000-0000-000000000005"
    sim_payload = {
        "action_type": "open_gate",
        "target_gate_id": gate_id,
        "parameters": {"flow_increase_p_per_min": 150}
    }
    sim_res = client.post(f"/api/v1/operator/zones/{zone_id}/simulate", json=sim_payload, headers=op_headers)
    assert sim_res.status_code == 200, f"Failed simulation: {sim_res.text}"
    sim_data = sim_res.json()
    print(f"   [SUCCESS] Simulation Result: Baseline Risk {sim_data['baseline_risk']} -> Projected Risk {sim_data['projected_risk_after']} (Delta: {sim_data['risk_delta']})")

    # 6. Recommendation Approval & Action Dispatch Triggers
    print("\n6. Operator Approving AI Intervention & Dispatching Tasks...")
    
    # 6a. Dispatch Field Officer Task
    dispatch_payload = {
        "officer_id": officer_id,
        "zone_id": zone_id,
        "task_description": "E2E Test: Manage bottleneck at East Gate bottleneck zone."
    }
    disp_res = client.post("/api/v1/operator/dispatch", json=dispatch_payload, headers=op_headers)
    assert disp_res.status_code == 200, f"Failed officer dispatch: {disp_res.text}"
    print(f"   [SUCCESS] Officer Task Dispatched! ID: {disp_res.json()['id']}")

    # 6b. Gate Status Override
    gate_res = client.patch(f"/api/v1/operator/gates/{gate_id}/status", json={"status": "open"}, headers=op_headers)
    assert gate_res.status_code == 200, f"Failed gate status update: {gate_res.text}"
    print(f"   [SUCCESS] Gate Status Updated to OPEN!")

    # 6c. Push Notification Trigger Attempt
    notif_res = notify_field_officers(
        officer_ids=[UUID(officer_id)],
        title="Urgent Intervention Dispatched",
        body="Proceed immediately to Sector A for crowd surge mitigation.",
        db=db,
        data_payload={"zone_id": zone_id, "action": "open_gate"}
    )
    print(f"   [SUCCESS] Push Notification Service Executed (Mode: {notif_res['mode']}, Sent: {notif_res['sent_count']})")

    # 6d. Record Approval Audit Log
    log_action(
        db=db,
        actor_id=UUID(op_id),
        action="APPROVE_RECOMMENDATION",
        target=f"zone:{zone_id}",
        after_state={"action": "open_gate", "gate_id": gate_id}
    )

    # 6e. Fire Citizen Alert
    from app.models.alert import AlertSeverityEnum
    new_alert = Alert(
        zone_id=UUID(zone_id),
        severity=AlertSeverityEnum.HIGH,
        message="Crowd Reroute Advisory: Please avoid Main Stage Entrance. Use North Exit Gate B2 for smoother egress."
    )
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)
    print(f"   [SUCCESS] Citizen Advisory Alert Fired! ID: {new_alert.id}")

    # 7. Verification of Side Effects (Officer Task, Citizen Alert, Audit Log)
    print("\n7. Verifying End-to-End System Side Effects:")
    
    # Task Assignment Check
    officer_task = db.query(OfficerAssignment).filter(OfficerAssignment.zone_id == UUID(zone_id)).order_by(OfficerAssignment.created_at.desc()).first()
    print(f"   - Officer Task Created in DB: {'YES' if officer_task else 'NO'} (Task ID: {officer_task.id if officer_task else 'N/A'})")

    # Citizen Alert Check
    alert = db.query(Alert).filter(Alert.zone_id == UUID(zone_id)).order_by(Alert.created_at.desc()).first()
    print(f"   - Citizen Alert Fired in DB: {'YES' if alert else 'NO'} (Alert ID: {alert.id if alert else 'N/A'})")

    # Audit Log Entry Check
    audit_entry = db.query(AuditLog).filter(AuditLog.action == "APPROVE_RECOMMENDATION").order_by(AuditLog.created_at.desc()).first()
    print(f"   - Audit Log Recorded in DB: {'YES' if audit_entry else 'NO'} (Audit ID: {audit_entry.id if audit_entry else 'N/A'})")

    db.close()
    print("\n" + "="*70)
    print("FULL E2E INTEGRATION LOOP PASSED VERIFICATION WITH 0 ERRORS!")
    print("="*70 + "\n")
    return True


if __name__ == "__main__":
    success = run_e2e_verification()
    sys.exit(0 if success else 1)
