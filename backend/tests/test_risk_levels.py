"""
TEST SUITE FOR STANDARDIZED RISK BUCKET TAXONOMY & MULTI-HORIZON ESCALATION
=============================================================================
"""

import pytest
from app.core.risk_levels import (
    RiskBucket,
    get_risk_bucket,
    evaluate_multi_horizon_risk,
    RISK_COLOR_PALETTE,
    RISK_THRESHOLDS
)


def test_standardized_risk_bucket_boundaries():
    """Verify raw 0-100 scores map precisely to the 4 standardized buckets."""
    assert get_risk_bucket(0.0) == RiskBucket.LOW
    assert get_risk_bucket(24.9) == RiskBucket.LOW
    assert get_risk_bucket(25.0) == RiskBucket.MODERATE
    assert get_risk_bucket(49.9) == RiskBucket.MODERATE
    assert get_risk_bucket(50.0) == RiskBucket.HIGH
    assert get_risk_bucket(74.9) == RiskBucket.HIGH
    assert get_risk_bucket(75.0) == RiskBucket.CRITICAL
    assert get_risk_bucket(100.0) == RiskBucket.CRITICAL


def test_palette_consistency():
    """Verify all RiskBucket keys have complete web & mobile color mappings."""
    for bucket in RiskBucket:
        palette = RISK_COLOR_PALETTE[bucket]
        assert "hex" in palette
        assert "web_bg" in palette
        assert "web_border" in palette
        assert "web_text" in palette
        assert "web_badge" in palette
        assert "mobile_bg" in palette


def test_multi_horizon_escalation_evaluation():
    """Verify evaluate_multi_horizon_risk flags future escalation accurately."""
    # Stable scenario
    stable_eval = evaluate_multi_horizon_risk(
        current_risk=15.0,
        risk_2min=18.0,
        risk_5min=20.0,
        risk_10min=22.0
    )
    assert not stable_eval["is_escalating"]
    assert stable_eval["current_bucket"] == "LOW"
    assert stable_eval["effective_bucket"] == "LOW"

    # Escalating scenario: LOW now -> CRITICAL at +5m
    escalation_eval = evaluate_multi_horizon_risk(
        current_risk=18.0,
        risk_2min=45.0,
        risk_5min=82.0,
        risk_10min=88.0
    )
    assert escalation_eval["is_escalating"]
    assert escalation_eval["current_bucket"] == "LOW"
    assert escalation_eval["max_forecast_bucket"] == "CRITICAL"
    assert escalation_eval["max_forecast_horizon"] == "10min"
    assert "CURRENTLY LOW, ESCALATING TO CRITICAL" in escalation_eval["trajectory_warning"]
    assert escalation_eval["effective_bucket"] == "CRITICAL"
