"""
CROWDSHIELD DISPATCH SERVICE
============================
Orchestrates automated execution when a Control Room Operator approves an AI risk recommendation.
Executes gate updates, officer dispatches, citizen safety alerts, push notifications, and audit logging.
"""

from typing import Dict, Any, Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.models import (
    AIRecommendation,
    Zone,
    Gate,
    OfficerAssignment,
    Alert,
    AlertSeverityEnum,
    User,
    UserRoleEnum
)
from app.services.audit_service import log_action
from app.services.push import notify_zone_citizens, notify_field_officers


def dispatch_approved_action(
    recommendation_id: UUID,
    db: Session,
    actor_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    Triggers complete dispatch workflow for an approved recommendation.
    """
    rec = db.query(AIRecommendation).filter(AIRecommendation.id == recommendation_id).first()
    if not rec:
        raise ValueError(f"AI Recommendation {recommendation_id} not found.")

    zone_id = rec.zone_id
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    zone_name = zone.name if zone else "Target Zone"

    actions_executed: List[str] = []
    dispatched_officer_ids: List[UUID] = []
    alert_created: Optional[Alert] = None

    # Parse recommended actions
    recommended_actions = rec.recommended_actions or []

    for action_item in recommended_actions:
        action_type = action_item.get("action_type", "").upper()

        # 1. Gate Override Execution
        if action_type in ["OPEN_EMERGENCY_GATE", "RESTRICT_ENTRY_GATE"]:
            target_gate_id_str = action_item.get("target_gate_id")
            if target_gate_id_str:
                target_gate = db.query(Gate).filter(Gate.id == UUID(target_gate_id_str)).first()
                if target_gate:
                    new_status = "open" if "OPEN" in action_type else "restricted"
                    before_status = target_gate.status
                    target_gate.status = new_status
                    actions_executed.append(f"Updated Gate '{target_gate.name}' status to {new_status}")

        # 2. Officer Squad Dispatch
        elif action_type in ["DISPATCH_FIELD_OFFICERS", "DISPATCH_OFFICERS"]:
            officer_count = action_item.get("recommended_officer_count", 2)
            # Fetch available field officers
            available_officers = db.query(User).filter(User.role == UserRoleEnum.FIELD_OFFICER.value).limit(officer_count).all()

            for officer in available_officers:
                assignment = OfficerAssignment(
                    officer_id=officer.id,
                    zone_id=zone_id,
                    task_description=f"AI DISPATCH: Manage crowd flow and clear bottlenecks in {zone_name}.",
                    status="assigned"
                )
                db.add(assignment)
                dispatched_officer_ids.append(officer.id)
            
            actions_executed.append(f"Dispatched {len(available_officers)} field officers to {zone_name}")

        # 3. Barricade Reconfiguration Execution (Prompt 2)
        elif action_type in ["RECONFIGURE_BARRICADE", "BARRICADE"]:
            barricade_id_str = action_item.get("target_barricade_id")
            new_config = action_item.get("new_configuration", "redirect_left")
            from app.models.barricade import Barricade, BarricadeConfigurationEnum
            
            barricade = None
            if barricade_id_str:
                try:
                    barricade = db.query(Barricade).filter(Barricade.id == UUID(barricade_id_str)).first()
                except Exception:
                    pass
            
            barricade_name = barricade.name if barricade else f"Barricade in {zone_name}"
            if barricade:
                try:
                    barricade.current_configuration = BarricadeConfigurationEnum(new_config)
                except Exception:
                    barricade.current_configuration = BarricadeConfigurationEnum.REDIRECT_LEFT
            
            # Dispatch Field Officer to physically execute barricade change
            available_officers = db.query(User).filter(User.role == UserRoleEnum.FIELD_OFFICER.value).limit(1).all()
            for officer in available_officers:
                assignment = OfficerAssignment(
                    officer_id=officer.id,
                    zone_id=zone_id,
                    task_description=f"AI DISPATCH: Reconfigure barricade '{barricade_name}' to {new_config} to clear choke point.",
                    status="assigned"
                )
                db.add(assignment)
                dispatched_officer_ids.append(officer.id)
            
            actions_executed.append(f"Reconfigured barricade '{barricade_name}' to {new_config} and assigned ground officer.")

        # 4. Citizen Safety Advisory & Rerouting Alert
        elif action_type in ["ISSUE_CITIZEN_REROUTE_ALERT", "CITIZEN_ADVISORY"]:
            severity = AlertSeverityEnum.HIGH if rec.risk_score > 70.0 else AlertSeverityEnum.MEDIUM
            alert_created = Alert(
                zone_id=zone_id,
                message=f"SAFETY ADVISORY: Heavy crowd density detected in {zone_name}. Please follow alternate routes.",
                severity=severity
            )
            db.add(alert_created)
            actions_executed.append(f"Published citizen safety alert for {zone_name}")

    db.commit()

    # 4. Trigger Push Notifications
    push_results = {}
    if alert_created:
        push_results["citizens"] = notify_zone_citizens(
            zone_id=zone_id,
            title="CrowdShield Safety Advisory",
            body=alert_created.message,
            db=db
        )

    if dispatched_officer_ids:
        push_results["officers"] = notify_field_officers(
            officer_ids=dispatched_officer_ids,
            title="New Emergency Task Assignment",
            body=f"You have been dispatched to {zone_name} for crowd surge management.",
            db=db
        )

    # 5. Write to Audit Log
    log_action(
        db=db,
        actor_id=actor_id,
        action="EXECUTE_APPROVED_DISPATCH",
        target=f"recommendation:{recommendation_id}",
        before_state={"status": "pending"},
        after_state={
            "status": "approved",
            "actions_executed": actions_executed,
            "dispatched_officer_ids": [str(i) for i in dispatched_officer_ids]
        }
    )

    return {
        "recommendation_id": str(recommendation_id),
        "zone_id": str(zone_id),
        "actions_executed": actions_executed,
        "dispatched_officers_count": len(dispatched_officer_ids),
        "alert_created": alert_created.message if alert_created else None,
        "push_notifications": push_results
    }
