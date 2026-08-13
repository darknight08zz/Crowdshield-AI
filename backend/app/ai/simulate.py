"""
CROWDSHIELD WHAT-IF INTERVENTION SIMULATION SERVICE
==================================================
Simulates proposed Control Room actions (gate opening/closing, flow redirection, officer dispatch, one-way enforcement)
by re-evaluating the XGBoost risk model against adjusted feature vectors.
"""

from typing import Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from app.ai.features import extract_zone_features
from app.ai.risk_model import predict_risk


def simulate_intervention(
    zone_id: Any,
    proposed_action: Dict[str, Any],
    db: Session
) -> Dict[str, Any]:
    """
    Executes what-if simulation for a proposed operator intervention.

    Args:
        zone_id: ID of the targeted zone.
        proposed_action: Dict containing "action_type", "target_gate_id", etc.
        db: SQLAlchemy DB Session.

    Returns:
        Dict[str, Any]:
            - baseline_risk: Risk score before intervention
            - projected_risk_after: Predicted risk score after proposed action
            - risk_delta: Net change in risk points (negative is improvement)
            - simulated_feature_changes: Adjusted feature vector comparison
    """
    # 1. Baseline feature extraction and current risk prediction
    baseline_features = extract_zone_features(zone_id=zone_id, db=db)
    baseline_risk_dict = predict_risk(baseline_features)
    baseline_risk = baseline_risk_dict["current_risk"]

    # 2. Clone feature vector to apply simulated adjustments
    sim_features = dict(baseline_features)

    action_type = str(proposed_action.get("action_type", "")).upper()
    action_text = str(proposed_action).upper()

    if action_type in ["ENFORCE_ONE_WAY_FLOW", "ONE_WAY_FLOW", "ENFORCE_ONE_WAY"] or "ONE_WAY" in action_text or "ENFORCE_ONE_WAY_FLOW" in action_text:
        # Enforcing one-way flow eliminates counter-directional movement and turbulence
        sim_features["reverse_flow_ratio"] = round(max(0.02, sim_features.get("reverse_flow_ratio", 0.05) * 0.25), 3)
        sim_features["direction_conflict_score"] = round(max(0.05, sim_features.get("direction_conflict_score", 0.15) * 0.30), 3)

    elif action_type in ["OPEN_EMERGENCY_GATE", "OPEN_GATE"] or "OPEN" in action_text:
        # Opening emergency/exit gate increases egress outflow capacity and lowers density build-up
        sim_features["outflow_rate"] = sim_features["outflow_rate"] + 80.0
        sim_features["gate_capacity_utilization"] = round(max(0.10, sim_features["gate_capacity_utilization"] - 0.25), 3)
        sim_features["direction_conflict_score"] = round(max(0.05, sim_features["direction_conflict_score"] - 0.15), 3)

    elif action_type in ["RESTRICT_ENTRY_GATE", "CLOSE_GATE", "RESTRICT_GATE"] or "RESTRICT" in action_text:
        # Restricting ingress cuts incoming flow rate
        sim_features["inflow_rate"] = round(max(10.0, sim_features["inflow_rate"] * 0.50), 1)
        sim_features["gate_capacity_utilization"] = round(max(0.10, sim_features["gate_capacity_utilization"] - 0.20), 3)

    elif action_type in ["DISPATCH_FIELD_OFFICERS", "DISPATCH_OFFICERS", "DEPLOY_OFFICERS"] or "OFFICER" in action_text:
        # Field officers improve movement order and pedestrian speed
        sim_features["avg_pedestrian_speed"] = round(min(1.40, sim_features["avg_pedestrian_speed"] + 0.25), 2)
        sim_features["direction_conflict_score"] = round(max(0.05, sim_features["direction_conflict_score"] - 0.20), 3)

    elif action_type in ["RECONFIGURE_BARRICADE", "BARRICADE"] or "BARRICADE" in action_text:
        # Reconfiguring internal barricades reshapes crowd flow, widening effective path & clearing stagnation
        sim_features["avg_pedestrian_speed"] = round(min(1.40, sim_features.get("avg_pedestrian_speed", 1.0) + 0.20), 2)
        sim_features["direction_conflict_score"] = round(max(0.05, sim_features.get("direction_conflict_score", 0.15) * 0.40), 3)
        sim_features["outflow_rate"] = round(sim_features.get("outflow_rate", 50.0) + 35.0, 1)

    elif action_type in ["ISSUE_CITIZEN_REROUTE_ALERT", "ISSUE_PUBLIC_ANNOUNCEMENT", "REROUTE_TRAFFIC"] or "ALERT" in action_text or "ANNOUNCEMENT" in action_text:
        # Public mobile alert diverts incoming citizens away from zone
        sim_features["inflow_rate"] = round(max(10.0, sim_features["inflow_rate"] * 0.65), 1)

    # 3. Re-evaluate XGBoost model with simulated features
    sim_risk_dict = predict_risk(sim_features)
    projected_risk_after = sim_risk_dict["current_risk"]
    projected_5min_after = sim_risk_dict["risk_5min"]

    risk_delta = round(projected_risk_after - baseline_risk, 1)

    return {
        "zone_id": str(zone_id),
        "proposed_action": proposed_action,
        "baseline_risk": baseline_risk,
        "projected_risk_after": projected_risk_after,
        "projected_5min_after": projected_5min_after,
        "risk_delta": risk_delta,
        "simulated_feature_changes": {
            "baseline": baseline_features,
            "adjusted": sim_features
        }
    }
