"""
CROWDSHIELD BEHAVIORAL CLASSIFICATION UNIT TEST SUITE
====================================================
Tests `classify_behavior` across all 5 behavioral pattern categories
with clearly-labeled synthetic input feature vectors.
"""

import pytest
from app.ai.behavior import classify_behavior, BehaviorType


def test_classify_normal_behavior():
    """
    Synthetic input representing normal, orderly pedestrian flow within safe thresholds.
    - Low/Moderate Density: 0.35
    - Balanced Inflow / Outflow: 75 / 70 peds/min
    - Normal Speed: 1.25 m/s
    - Low Conflict & Reverse Flow: 0.10 conflict, 0.05 reverse flow
    - Low Blockage: 0.10
    - No Active Incidents: 0.0
    """
    features = {
        "current_density": 0.35,
        "inflow_rate": 75.0,
        "outflow_rate": 70.0,
        "avg_pedestrian_speed": 1.25,
        "direction_conflict_score": 0.10,
        "gate_capacity_utilization": 0.45,
        "recent_incident_count_10min": 0.0,
        "reverse_flow_ratio": 0.05,
        "blockage_score": 0.10
    }
    result = classify_behavior(features)
    assert result == BehaviorType.NORMAL
    assert result.value == "NORMAL"


def test_classify_stagnation_behavior():
    """
    Synthetic input representing physical route blockage / gridlock:
    - High Density: 0.82
    - Severe Speed Drop: 0.28 m/s (< 0.45 m/s threshold)
    - High Spatially-Concentrated Blockage Score: 0.78 (>= 0.45 threshold)
    """
    features = {
        "current_density": 0.82,
        "inflow_rate": 90.0,
        "outflow_rate": 40.0,
        "avg_pedestrian_speed": 0.28,
        "direction_conflict_score": 0.30,
        "gate_capacity_utilization": 0.85,
        "recent_incident_count_10min": 0.0,
        "reverse_flow_ratio": 0.15,
        "blockage_score": 0.78
    }
    result = classify_behavior(features)
    assert result == BehaviorType.STAGNATION
    assert result.value == "STAGNATION"


def test_classify_dispersed_incident_cluster_behavior():
    """
    Synthetic input representing multiple active incidents in last 10 minutes:
    - Recent Incident Count: 2.0 (>= 2.0 threshold)
    """
    features = {
        "current_density": 0.55,
        "inflow_rate": 80.0,
        "outflow_rate": 75.0,
        "avg_pedestrian_speed": 0.95,
        "direction_conflict_score": 0.25,
        "gate_capacity_utilization": 0.50,
        "recent_incident_count_10min": 2.0,
        "reverse_flow_ratio": 0.10,
        "blockage_score": 0.20
    }
    result = classify_behavior(features)
    assert result == BehaviorType.DISPERSED_INCIDENT_CLUSTER
    assert result.value == "DISPERSED_INCIDENT_CLUSTER"


def test_classify_reverse_flow_behavior():
    """
    Synthetic input representing significant counter-directional movement:
    - High Reverse Flow Ratio: 0.42 (>= 0.35 threshold)
    - High Directional Turbulence Conflict: 0.65 (>= 0.60 threshold)
    """
    features = {
        "current_density": 0.58,
        "inflow_rate": 85.0,
        "outflow_rate": 80.0,
        "avg_pedestrian_speed": 0.90,
        "direction_conflict_score": 0.65,
        "gate_capacity_utilization": 0.60,
        "recent_incident_count_10min": 0.0,
        "reverse_flow_ratio": 0.42,
        "blockage_score": 0.25
    }
    result = classify_behavior(features)
    assert result == BehaviorType.REVERSE_FLOW
    assert result.value == "REVERSE_FLOW"


def test_classify_surge_behavior():
    """
    Synthetic input representing rapid inward crowd compression surge:
    - Inflow Velocity: 175.0 peds/min (>= 140.0 threshold)
    - Net Flow Imbalance: Inflow (175) - Outflow (60) = 115 peds/min (>= 40.0 threshold)
    - Elevated Density: 0.68 (>= 0.55 threshold)
    """
    features = {
        "current_density": 0.68,
        "inflow_rate": 175.0,
        "outflow_rate": 60.0,
        "avg_pedestrian_speed": 0.85,
        "direction_conflict_score": 0.25,
        "gate_capacity_utilization": 0.80,
        "recent_incident_count_10min": 0.0,
        "reverse_flow_ratio": 0.12,
        "blockage_score": 0.20
    }
    result = classify_behavior(features)
    assert result == BehaviorType.SURGE
    assert result.value == "SURGE"
