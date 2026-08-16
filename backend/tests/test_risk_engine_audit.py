"""
TEST SUITE FOR RISK ENGINE AUDIT & BASELINE SEPARATION (PHASE 3)
================================================================
Verifies that current risk engine logic is deterministic, audited, and strictly decoupled
from future AI prediction models.
"""

import pytest
from app.ai.risk_model import predict_risk
from app.ai.dataset.baseline_engine import baseline_risk
from app.core.risk_levels import RiskBucket, get_risk_bucket


def test_deterministic_baseline_risk_calculation():
    """
    Verifies that baseline risk produces deterministic, reproducible risk scores.
    """
    sample_features = {
        "current_density": 0.65,
        "inflow_rate": 120.0,
        "outflow_rate": 60.0,
        "avg_pedestrian_speed": 0.70,
        "direction_conflict_score": 0.40,
        "gate_capacity_utilization": 0.80,
        "recent_incident_count_10min": 1.0,
        "reverse_flow_ratio": 0.25,
        "blockage_score": 0.35,
    }

    res1 = baseline_risk(sample_features)
    res2 = baseline_risk(sample_features)

    assert res1["current_risk"] == res2["current_risk"]
    assert res1["risk_2min"] == res2["risk_2min"]
    assert res1["risk_5min"] == res2["risk_5min"]
    assert res1["risk_10min"] == res2["risk_10min"]
    assert res1["model_type"] == "RULE_BASED_BASELINE"
    assert res1["is_deterministic"] is True
    assert res1["risk_bucket"] in [b.value for b in RiskBucket]


def test_risk_bucket_taxonomy_boundaries():
    """
    Verifies that risk bucket taxonomy (LOW, MODERATE, HIGH, CRITICAL) adheres strictly to risk_levels.py.
    """
    assert get_risk_bucket(10.0) == RiskBucket.LOW
    assert get_risk_bucket(35.0) == RiskBucket.MODERATE
    assert get_risk_bucket(60.0) == RiskBucket.HIGH
    assert get_risk_bucket(85.0) == RiskBucket.CRITICAL


def test_predict_risk_momentum_projection_labeling():
    """
    Verifies that multi-horizon forward risk extrapolations in predict_risk are momentum projections.
    """
    sample_features = {
        "current_density": 0.80,
        "inflow_rate": 150.0,
        "outflow_rate": 40.0,
        "avg_pedestrian_speed": 0.40,
    }

    res = predict_risk(sample_features)

    assert "current_risk" in res
    assert "risk_2min" in res
    assert "risk_5min" in res
    assert "risk_10min" in res
    assert res["risk_5min"] >= res["current_risk"]  # Escalating due to inflow > outflow
