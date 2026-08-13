"""
CROWDSHIELD FAILOVER LOUDNESS TEST SUITE
========================================
Verifies that system failures, camera dropouts, and AI model exceptions fail loud
with clear visual indicators (is_degraded: true, degraded status headers) rather than failing silent.
"""

import pytest
from app.ingestion.hybrid_cctv_gps import HybridCCTVGPSIngestion
from app.ingestion.quality import evaluate_telemetry_quality
from app.ai.features import extract_zone_features


def test_camera_offline_fails_loud():
    """Verify missing CCTV telemetry reports is_degraded: true and low confidence."""
    empty_hybrid = HybridCCTVGPSIngestion()
    features = empty_hybrid.get_zone_features("bb222222-0000-0000-0000-000000000002", db=None)

    assert features["is_degraded"] is True
    assert features["confidence_score"] < 0.50
    assert "quality_breakdown" in features
    assert features["quality_breakdown"]["camera_uptime_score"] == 0.0


def test_exception_in_ingestion_fails_loud():
    """Verify exceptions in live ingestion trigger instant fallback tagged as degraded."""
    hybrid = HybridCCTVGPSIngestion()
    # Pass bad zone string to trigger exception handling
    features = hybrid.get_zone_features(None, db=None)

    assert features["is_degraded"] is True
    assert features["confidence_score"] <= 0.30
