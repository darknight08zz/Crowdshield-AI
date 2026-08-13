"""
CROWDSHIELD INTERPRETABLE RECOMMENDATION ENGINE
===============================================
Maps risk levels, behavioral patterns, and specific crowd risk drivers to a deterministic,
ranked list of actionable interventions for Control Room Operators.
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.gate import Gate, GateStatusEnum
from app.models.zone import Zone
from app.core.policy import get_current_notification_policy
from app.core.risk_levels import get_risk_bucket, RiskBucket, evaluate_multi_horizon_risk
from app.ai.behavior import classify_behavior, BehaviorType


def is_valid_uuid(val: Any) -> bool:
    if not val:
        return False
    try:
        UUID(str(val))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def generate_recommendations(
    zone_id: Any,
    current_risk: float,
    predicted_risk_5min: float,
    feature_dict: Dict[str, float],
    db: Session,
    risk_trajectory: Optional[Dict[str, float]] = None
) -> List[Dict[str, Any]]:
    """
    Evaluates rule-based intervention logic keyed off physical risk drivers, behavior classification,
    and standardized RiskBucket values derived from the single source of truth.

    Returns:
        List[Dict[str, Any]]: Ranked list of recommended action objects.
    """
    recommendations: List[Dict[str, Any]] = []

    # Evaluate multi-horizon risk and risk bucket
    curr_bucket = get_risk_bucket(current_risk)
    r2m = risk_trajectory.get("risk_2min") if risk_trajectory else None
    r5m = risk_trajectory.get("risk_5min", predicted_risk_5min) if risk_trajectory else predicted_risk_5min
    r10m = risk_trajectory.get("risk_10min") if risk_trajectory else None
    
    mh_eval = evaluate_multi_horizon_risk(current_risk, r2m, r5m, r10m)

    # Classify crowd behavioral pattern
    behavior = classify_behavior(feature_dict)

    if curr_bucket == RiskBucket.LOW and not mh_eval["is_escalating"] and behavior == BehaviorType.NORMAL:
        return [{
            "priority": 1,
            "action_type": "MONITOR_STABLE",
            "title": "Maintain Normal Operational Monitoring",
            "description": "Zone parameters are within LOW risk thresholds (0-24). Continue automated telemetry checks.",
            "target": f"zone:{zone_id}",
            "expected_impact": "Prevents unnecessary officer fatigue or panic alerts.",
            "require_operator_approval": False,
            "inform_citizen": False
        }]

    # Fetch associated gates for explicit targeted recommendations
    zone_str = str(zone_id)
    gates = db.query(Gate).filter(Gate.zone_id == UUID(zone_str)).all() if is_valid_uuid(zone_str) else []
    closed_emergency_gates = [g for g in gates if g.type == "emergency" and g.status == "closed"]
    restricted_entry_gates = [g for g in gates if g.type == "entry" and g.status == "open"]

    density = feature_dict.get("current_density", 0.50)
    inflow = feature_dict.get("inflow_rate", 80.0)
    outflow = feature_dict.get("outflow_rate", 80.0)
    speed = feature_dict.get("avg_pedestrian_speed", 1.20)
    incidents = feature_dict.get("recent_incident_count_10min", 0.0)
    reverse_flow = feature_dict.get("reverse_flow_ratio", 0.05)

    priority_counter = 1

    # Rule 1: Special Action - ENFORCE_ONE_WAY_FLOW specifically for REVERSE_FLOW behavior
    if behavior == BehaviorType.REVERSE_FLOW or reverse_flow >= 0.35:
        route_id = f"route-{zone_str[:8]}"
        recommendations.append({
            "priority": priority_counter,
            "action_type": "ENFORCE_ONE_WAY_FLOW",
            "title": f"Enforce One-Way Pedestrian Route ({route_id})",
            "description": f"Deploy directional barriers and staff near route {route_id} to enforce one-way flow and eliminate counter-directional movement.",
            "target": f"zone:{zone_id}",
            "route_id": route_id,
            "expected_impact": "Eliminates reverse-flow turbulence and cuts direction conflict score by ~70%."
        })
        priority_counter += 1

    # Rule 2: Emergency Gate Opening for severe congestion / crushing risk or CRITICAL risk bucket
    if (density > 0.75 or curr_bucket == RiskBucket.CRITICAL or mh_eval["max_forecast_bucket"] == RiskBucket.CRITICAL.value or behavior == BehaviorType.STAGNATION) and closed_emergency_gates:
        target_gate = closed_emergency_gates[0]
        recommendations.append({
            "priority": priority_counter,
            "action_type": "OPEN_EMERGENCY_GATE",
            "title": f"Open Emergency Exit '{target_gate.name}'",
            "description": f"Immediately open {target_gate.name} to release bottleneck pressure and increase egress by {target_gate.capacity_per_min} peds/min.",
            "target_gate_id": str(target_gate.id),
            "target": f"gate:{target_gate.id}",
            "expected_impact": "Reduces zone risk score by ~25% within 3 minutes."
        })
        priority_counter += 1

    # Rule 3: Restrict Ingress Gate if inflow exceeds outflow or SURGE pattern detected
    if (inflow > outflow + 30 or behavior == BehaviorType.SURGE) and restricted_entry_gates:
        target_gate = restricted_entry_gates[0]
        recommendations.append({
            "priority": priority_counter,
            "action_type": "RESTRICT_ENTRY_GATE",
            "title": f"Restrict Entry Gate '{target_gate.name}'",
            "description": f"Throttle ingress rate at {target_gate.name} to prevent further accumulation in zone.",
            "target_gate_id": str(target_gate.id),
            "target": f"gate:{target_gate.id}",
            "expected_impact": "Cuts incoming flow delta by 40%."
        })
        priority_counter += 1

    # Rule 4: Field Officer Deployment
    if density > 0.65 or speed < 0.80 or incidents > 0 or curr_bucket in [RiskBucket.HIGH, RiskBucket.CRITICAL]:
        recommended_officer_count = 4 if curr_bucket == RiskBucket.CRITICAL else 2
        recommendations.append({
            "priority": priority_counter,
            "action_type": "DISPATCH_FIELD_OFFICERS",
            "title": f"Dispatch {recommended_officer_count} Field Officers",
            "description": f"Deploy a squad of {recommended_officer_count} field officers to assist crowd flow direction and clear bottlenecks.",
            "recommended_officer_count": recommended_officer_count,
            "target": f"zone:{zone_id}",
            "expected_impact": "Restores pedestrian velocity and verifies ground conditions."
        })
        priority_counter += 1

    # Rule 5: Barricade Configuration Action (Prompt 2)
    # Triggered when internal zone choke-points or stagnation require physical flow shaping
    barricades = []
    if is_valid_uuid(zone_str):
        from app.models.barricade import Barricade
        barricades = db.query(Barricade).filter(Barricade.zone_id == UUID(zone_str)).all()

    if density > 0.60 or behavior in [BehaviorType.STAGNATION, BehaviorType.SURGE] or feature_dict.get("direction_conflict_score", 0.0) > 0.15:
        target_barricade = barricades[0] if barricades else None
        barricade_id_str = str(target_barricade.id) if target_barricade else f"barricade-{zone_str[:8]}"
        barricade_name = target_barricade.name if target_barricade else f"Zone Flow Barricade #{zone_str[:4]}"
        
        recommendations.append({
            "priority": priority_counter,
            "action_type": "RECONFIGURE_BARRICADE",
            "title": f"Reconfigure Barricade '{barricade_name}'",
            "description": f"Adjust internal flow divider '{barricade_name}' to redirect_left configuration to relieve localized choke point.",
            "target_barricade_id": barricade_id_str,
            "new_configuration": "redirect_left",
            "target": f"barricade:{barricade_id_str}",
            "expected_impact": "Physically shapes internal crowd flow, widening effective bottleneck path by ~30% and eliminating localized stagnation."
        })
        priority_counter += 1

    # Rule 6: Citizen Mobile Advisory / Public Announcement
    if curr_bucket in [RiskBucket.MODERATE, RiskBucket.HIGH, RiskBucket.CRITICAL] or mh_eval["is_escalating"] or behavior != BehaviorType.NORMAL:
        recommendations.append({
            "priority": priority_counter,
            "action_type": "ISSUE_PUBLIC_ANNOUNCEMENT",
            "title": "Broadcast Public Venue Announcement & Citizen Mobile Advisory",
            "description": "Broadcast automated public address announcement and push mobile alert to divert incoming traffic.",
            "target": f"zone:{zone_id}",
            "expected_impact": "Diverts incoming foot traffic by 25-35% within 5 minutes."
        })
        priority_counter += 1

    # Apply active notification policy rules using standardized bucket names
    policy = get_current_notification_policy()
    policy_key = curr_bucket.value
    if policy_key not in policy and curr_bucket == RiskBucket.MODERATE:
        policy_key = "MEDIUM"

    rule = policy.get(policy_key, policy.get(curr_bucket.value, {}))
    for rec in recommendations:
        rec["require_operator_approval"] = rule.get("require_operator_approval", True)
        rec["inform_citizen"] = rule.get("inform_citizen", False)

    return recommendations
