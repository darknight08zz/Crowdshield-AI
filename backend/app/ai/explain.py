"""
CROWDSHIELD EXPLAINABLE AI (XAI) MODULE
=======================================
Translates numerical risk scores, feature vectors, and behavioral pattern classifications
into plain-language explanations and primary risk drivers for Control Room Operators.
"""

from typing import Dict, Any, List, Optional
from app.ai.features import SAFE_BASELINES
from app.ai.behavior import classify_behavior, BehaviorType


def explain_risk_score(
    current_risk: float,
    feature_dict: Dict[str, float],
    behavior: Optional[BehaviorType] = None,
    risk_trajectory: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Analyzes feature vector deviations, behavior classifications, and multi-horizon risk trajectory shape.

    Returns:
        Dict[str, Any]:
          - "summary": Operator-facing textual explanation referencing crowd behavior pattern, trajectory trend, and key drivers
          - "top_risk_factors": List of top driving factors with percentage deviations
          - "trajectory_trend": "RAPID_ESCALATION" | "ELEVATED_STABILIZING" | "MODERATE_BUILDUP" | "STABLE"
    """
    if behavior is None:
        behavior = classify_behavior(feature_dict)

    behavior_str = behavior.value if hasattr(behavior, "value") else str(behavior)

    # Evaluate trajectory trend shape
    trend_type = "STABLE"
    trend_msg = ""
    if risk_trajectory:
        r2 = risk_trajectory.get("risk_2min", current_risk)
        r5 = risk_trajectory.get("risk_5min", current_risk)
        r10 = risk_trajectory.get("risk_10min", current_risk)

        if r10 - current_risk >= 15.0 or r5 - current_risk >= 10.0:
            trend_type = "RAPID_ESCALATION"
            trend_msg = f" TRAJECTORY CRITICAL: Risk is rising rapidly (Current {current_risk:.1f} -> +5m {r5:.1f} -> +10m {r10:.1f}). Immediate proactive intervention recommended."
        elif current_risk >= 50.0 and (r10 - current_risk <= 5.0):
            trend_type = "ELEVATED_STABILIZING"
            trend_msg = f" TRAJECTORY STABILIZING: Risk is elevated ({current_risk:.1f}) but projected to plateau at +10m ({r10:.1f}). Monitor without panic dispatch."
        elif r10 - current_risk >= 6.0:
            trend_type = "MODERATE_BUILDUP"
            trend_msg = f" TRAJECTORY BUILDUP: Gradual accumulation forecast (Current {current_risk:.1f} -> +10m {r10:.1f})."

    if current_risk < 30.0 and behavior == BehaviorType.NORMAL and trend_type == "STABLE":
        return {
            "summary": f"Zone operating within safe parameters (Risk Level: Low {current_risk:.1f}/100, Pattern: {behavior_str}). Crowd movement is orderly and gate capacities are healthy.",
            "top_risk_factors": [],
            "trajectory_trend": "STABLE"
        }

    # Evaluate feature deviations relative to safe baseline bounds
    factors: List[Dict[str, Any]] = []

    # Behavior-specific primary contextual messages
    if behavior == BehaviorType.REVERSE_FLOW:
        rev_ratio = feature_dict.get("reverse_flow_ratio", 0.05)
        factors.append({
            "feature": "Reverse Flow Anomaly",
            "impact_score": 50.0,
            "message": f"Movement is flowing against designated direction (Reverse Flow Ratio: {int(rev_ratio * 100)}%)."
        })
    elif behavior == BehaviorType.STAGNATION:
        block_score = feature_dict.get("blockage_score", 0.10)
        factors.append({
            "feature": "Spatially-Concentrated Route Blockage",
            "impact_score": 55.0,
            "message": f"Physical route blockage detected with sustained speed drop in sub-area (Blockage Index: {int(block_score * 100)}%)."
        })
    elif behavior == BehaviorType.SURGE:
        inflow = feature_dict.get("inflow_rate", 80.0)
        outflow = feature_dict.get("outflow_rate", 80.0)
        factors.append({
            "feature": "Crowd Compression Surge",
            "impact_score": 45.0,
            "message": f"Crowd compression surge: Inflow ({int(inflow)} peds/min) outpaces egress outflow ({int(outflow)} peds/min)."
        })
    elif behavior == BehaviorType.DISPERSED_INCIDENT_CLUSTER:
        incidents = feature_dict.get("recent_incident_count_10min", 0.0)
        factors.append({
            "feature": "Dispersed Incident Cluster",
            "impact_score": 48.0,
            "message": f"Dispersed incident cluster active ({int(incidents)} reports in 10 mins) causing multi-point disruptions."
        })

    # Quantitative feature factor evaluations
    density = feature_dict.get("current_density", 0.40)
    if density > 0.60:
        pct_over = int(((density - SAFE_BASELINES["current_density"]) / SAFE_BASELINES["current_density"]) * 100)
        factors.append({
            "feature": "Occupancy Density",
            "impact_score": (density - 0.40) * 40,
            "message": f"Occupancy density is at {int(density * 100)}% ({pct_over}% above safe threshold)."
        })

    inflow = feature_dict.get("inflow_rate", 80.0)
    outflow = feature_dict.get("outflow_rate", 80.0)
    if inflow > outflow + 20 and behavior != BehaviorType.SURGE:
        diff_pct = int(((inflow - outflow) / max(1.0, outflow)) * 100)
        factors.append({
            "feature": "Inflow/Outflow Imbalance",
            "impact_score": (inflow - outflow) * 0.25,
            "message": f"Crowd inflow ({int(inflow)} peds/min) exceeds outflow ({int(outflow)} peds/min) by {diff_pct}%."
        })

    speed = feature_dict.get("avg_pedestrian_speed", 1.20)
    if speed < 0.90 and behavior != BehaviorType.STAGNATION:
        speed_drop = int(((SAFE_BASELINES["avg_pedestrian_speed"] - speed) / SAFE_BASELINES["avg_pedestrian_speed"]) * 100)
        factors.append({
            "feature": "Pedestrian Stagnation",
            "impact_score": (1.20 - speed) * 30,
            "message": f"Pedestrian walking speed has dropped by {speed_drop}% to {speed:.2f} m/s."
        })

    conflict = feature_dict.get("direction_conflict_score", 0.15)
    if conflict > 0.40 and behavior != BehaviorType.REVERSE_FLOW:
        factors.append({
            "feature": "Directional Turbulence",
            "impact_score": conflict * 25,
            "message": f"High counter-flow turbulence detected (Conflict Index: {int(conflict * 100)}%)."
        })

    reverse_flow = feature_dict.get("reverse_flow_ratio", 0.05)
    if reverse_flow > 0.30 and behavior != BehaviorType.REVERSE_FLOW:
        factors.append({
            "feature": "Reverse Flow Anomaly",
            "impact_score": reverse_flow * 30,
            "message": f"Movement is flowing against designated direction (Reverse Flow Ratio: {int(reverse_flow * 100)}%)."
        })

    blockage = feature_dict.get("blockage_score", 0.10)
    if blockage > 0.40 and behavior != BehaviorType.STAGNATION:
        factors.append({
            "feature": "Route Blockage",
            "impact_score": blockage * 35,
            "message": f"Spatially-concentrated speed drop detected in sub-area (Blockage Index: {int(blockage * 100)}%)."
        })

    gate_util = feature_dict.get("gate_capacity_utilization", 0.50)
    if gate_util > 0.75:
        factors.append({
            "feature": "Gate Chokepoint Bottleneck",
            "impact_score": gate_util * 20,
            "message": f"Gate capacity utilization is critical at {int(gate_util * 100)}%."
        })

    incidents = feature_dict.get("recent_incident_count_10min", 0.0)
    if incidents > 0 and behavior != BehaviorType.DISPERSED_INCIDENT_CLUSTER:
        factors.append({
            "feature": "Active Incidents",
            "impact_score": incidents * 15,
            "message": f"{int(incidents)} incident report(s) active in zone in last 10 minutes."
        })

    # Sort factors by impact score
    factors.sort(key=lambda x: x["impact_score"], reverse=True)

    top_messages = [f["message"] for f in factors[:3]]
    if top_messages:
        explanation_text = f"Elevated Risk ({current_risk:.1f}/100, Pattern: {behavior_str}) driven by: " + " ".join(top_messages) + trend_msg
    else:
        explanation_text = f"Moderate Risk ({current_risk:.1f}/100, Pattern: {behavior_str}) detected due to elevated localized crowd activity." + trend_msg

    return {
        "summary": explanation_text,
        "top_risk_factors": [{"factor": f["feature"], "detail": f["message"]} for f in factors[:3]],
        "trajectory_trend": trend_type
    }
