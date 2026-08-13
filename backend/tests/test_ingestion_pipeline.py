"""
CROWDSHIELD REAL INGESTION PIPELINE TEST SUITE
==============================================
Tests live Hybrid CCTV/GPS ingestion, fallback mechanisms, data quality evaluation,
and confidence score tracking.
"""

import pytest
import os
from uuid import UUID
from datetime import datetime, timedelta, timezone

from conftest import TestingSessionLocal as SessionLocal
from app.ingestion.quality import evaluate_telemetry_quality
from app.ingestion.synthetic import SyntheticSensorIngestion
from app.ingestion.hybrid_cctv_gps import HybridCCTVGPSIngestion
from app.ingestion.factory import get_ingestion_adapter
from app.ai.features import extract_zone_features


def test_synthetic_ingestion_adapter():
    """Verify synthetic adapter returns correct features and metadata."""
    db = SessionLocal()
    adapter = SyntheticSensorIngestion()
    features = adapter.get_zone_features("aa111111-0000-0000-0000-000000000001", db)

    assert "current_density" in features
    assert "inflow_rate" in features
    assert features["confidence_score"] == 0.85
    assert features["telemetry_source"] == "synthetic_fallback"
    assert features["is_degraded"] is False
    db.close()


def test_telemetry_quality_evaluation():
    """Verify quality score decay with feed age and missing camera uptime."""
    # 1. Fresh telemetry with full cameras
    fresh_q = evaluate_telemetry_quality(feed_age_seconds=2.0, active_cameras_ratio=1.0, gps_sample_count=20)
    assert fresh_q["confidence_score"] == 1.0
    assert fresh_q["is_degraded"] is False

    # 2. Stale telemetry (25 sec age)
    stale_q = evaluate_telemetry_quality(feed_age_seconds=25.0, active_cameras_ratio=0.5, gps_sample_count=5)
    assert stale_q["confidence_score"] < 0.50
    assert stale_q["is_degraded"] is True


def test_hybrid_cctv_gps_ingestion_and_fallback():
    """Verify live camera buffer updates and automatic fallback when feed drops."""
    db = SessionLocal()
    hybrid = HybridCCTVGPSIngestion()
    zone_id = "aa111111-0000-0000-0000-000000000001"

    # 1. Feed camera telemetry
    hybrid.update_camera_telemetry(
        zone_id=zone_id,
        camera_data={
            "density_peds_m2": 2.4,
            "inflow_peds_min": 120.0,
            "outflow_peds_min": 40.0,
            "avg_speed_ms": 0.65,
            "reverse_flow_ratio": 0.42,
            "blockage_score": 0.55,
            "direction_conflict_score": 0.60,
            "active_cameras": 4,
            "total_cameras": 4
        }
    )

    features = hybrid.get_zone_features(zone_id, db)
    assert features["telemetry_source"] == "live_cctv_gps"
    assert features["inflow_rate"] == 120.0
    assert features["reverse_flow_ratio"] == 0.42
    assert features["confidence_score"] > 0.70

    # 2. Test fallback when zone buffer is empty
    empty_hybrid = HybridCCTVGPSIngestion()
    fallback_features = empty_hybrid.get_zone_features("bb222222-0000-0000-0000-000000000002", db)
    assert fallback_features["is_degraded"] is True
    assert "current_density" in fallback_features

    db.close()


def test_ingestion_factory_mode_switch():
    """Verify SENSOR_MODE config switching."""
    synthetic_adapter = get_ingestion_adapter("synthetic")
    assert isinstance(synthetic_adapter, SyntheticSensorIngestion)

    live_adapter = get_ingestion_adapter("live")
    assert isinstance(live_adapter, HybridCCTVGPSIngestion)
