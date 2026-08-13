"""
CROWDSHIELD BEHAVIORAL PATTERN CLASSIFIER
=========================================
Provides rule-based, explainable classification of crowd behavior patterns based on
extracted zone feature vectors. Uses transparent physical thresholds for reviewer auditability.
"""

import enum
from typing import Dict, Any


class BehaviorType(str, enum.Enum):
    NORMAL = "NORMAL"
    SURGE = "SURGE"
    REVERSE_FLOW = "REVERSE_FLOW"
    STAGNATION = "STAGNATION"
    DISPERSED_INCIDENT_CLUSTER = "DISPERSED_INCIDENT_CLUSTER"


def classify_behavior(feature_vector: Dict[str, Any]) -> BehaviorType:
    """
    Classifies crowd movement state into one of 5 explainable categories.

    Threshold Rationale & Reviewer Justification:
    ---------------------------------------------
    1. STAGNATION:
       - Trigger: speed < 0.45 m/s AND blockage_score >= 0.45 AND current_density >= 0.60
         (or blockage_score >= 0.70 with speed < 0.50).
       - Justification: Identifies a sustained, spatially-concentrated speed drop in one sub-area of the zone.
         This distinguishes physical route blockage / gridlock from uniform crowd accumulation.

    2. DISPERSED_INCIDENT_CLUSTER:
       - Trigger: recent_incident_count_10min >= 2.0.
       - Justification: Indicates multiple active citizen/operator incident reports in the last 10 minutes,
         reflecting multi-point localized disruptions or scattered panic clusters.

    3. REVERSE_FLOW:
       - Trigger: reverse_flow_ratio >= 0.35 OR direction_conflict_score >= 0.60.
       - Justification: Detects when >= 35% of tracked movement is moving counter to the zone's
         designated flow vector, creating turbulent counter-currents.

    4. SURGE:
       - Trigger: (inflow_rate >= 140.0 OR inflow_rate - outflow_rate >= 40.0) AND current_density >= 0.55.
       - Justification: Detects rapid inward accumulation where ingress flow velocity significantly outpaces
         egress capacity, causing high compression velocity.

    5. NORMAL:
       - Trigger: Baseline default when no critical anomaly thresholds are breached.
       - Justification: Represents orderly pedestrian movement within safe operating bounds.
    """
    density = float(feature_vector.get("current_density", 0.40))
    inflow = float(feature_vector.get("inflow_rate", 80.0))
    outflow = float(feature_vector.get("outflow_rate", 80.0))
    speed = float(feature_vector.get("avg_pedestrian_speed", 1.20))
    conflict = float(feature_vector.get("direction_conflict_score", 0.15))
    incidents = float(feature_vector.get("recent_incident_count_10min", 0.0))
    reverse_flow = float(feature_vector.get("reverse_flow_ratio", 0.05))
    blockage = float(feature_vector.get("blockage_score", 0.10))

    # Evaluate safety-critical anomalies in priority order

    # 1. Stagnation / Localized Route Blockage
    if (speed < 0.45 and blockage >= 0.45 and density >= 0.60) or (blockage >= 0.70 and speed < 0.50):
        return BehaviorType.STAGNATION

    # 2. Dispersed Incident Cluster
    if incidents >= 2.0:
        return BehaviorType.DISPERSED_INCIDENT_CLUSTER

    # 3. Reverse Flow (counter-directional movement)
    if reverse_flow >= 0.35 or conflict >= 0.60:
        return BehaviorType.REVERSE_FLOW

    # 4. Inflow Compression Surge
    if (inflow >= 140.0 or (inflow - outflow >= 40.0)) and density >= 0.55:
        return BehaviorType.SURGE

    # 5. Normal Operational State
    return BehaviorType.NORMAL
