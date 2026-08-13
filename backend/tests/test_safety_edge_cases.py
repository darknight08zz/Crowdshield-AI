"""
CROWDSHIELD SAFETY-CRITICAL EDGE-CASE TEST SUITE
================================================
Tests sensor dropout mid-event, sudden gate status changes, zero GPS app users,
and conflicting sensor signals (e.g. high CCTV density vs zero GPS pings).
"""

import pytest
from datetime import datetime, timezone
from conftest import TestingSessionLocal as SessionLocal
from app.ingestion.hybrid_cctv_gps import HybridCCTVGPSIngestion
from app.ingestion.quality import evaluate_telemetry_quality
from app.ai.features import extract_zone_features
from app.ai.risk_model import predict_risk


def test_edge_case_cctv_sensor_dropout_midevent():
    """
    EDGE CASE 1: CCTV Camera stream drops mid-event.
    Verifies that when feed age > 30s, system tags reading as degraded with low confidence
    instead of presenting stale numbers as solid data.
    """
    db = SessionLocal()
    hybrid = HybridCCTVGPSIngestion()
    zone_id = "aa111111-0000-0000-0000-000000000001"

    # 1. Active feed at t=0
    hybrid.update_camera_telemetry(zone_id, {
        "density_peds_m2": 2.2,
        "inflow_peds_min": 110.0,
        "outflow_peds_min": 90.0,
        "avg_speed_ms": 0.85,
        "active_cameras": 4,
        "total_cameras": 4
    })
    # Manually age the timestamp by 45 seconds (dropped stream)
    hybrid.camera_buffers[zone_id]["timestamp"] = datetime.now(timezone.utc) - pytest.importorskip("datetime").timedelta(seconds=45)

    features = hybrid.get_zone_features(zone_id, db)
    assert features["is_degraded"] is True
    assert features["confidence_score"] < 0.50
    assert features["telemetry_source"] == "live_cctv_gps"
    db.close()


def test_edge_case_sudden_gate_restriction():
    """
    EDGE CASE 2: Sudden gate restriction/closure mid-event during high inflow.
    Verifies gate capacity utilization surges and projected risk increases.
    """
    db = SessionLocal()
    zone_id = "aa111111-0000-0000-0000-000000000001"

    # Low-density baseline features
    low_density_features = {
        "current_density": 0.25,
        "inflow_rate": 40.0,
        "outflow_rate": 40.0,
        "avg_pedestrian_speed": 1.30,
        "direction_conflict_score": 0.10,
        "gate_capacity_utilization": 0.30,
        "recent_incident_count_10min": 0,
        "reverse_flow_ratio": 0.05,
        "blockage_score": 0.08
    }

    # Congested features with high density & restricted gates
    congested_features = {
        "current_density": 0.75,
        "inflow_rate": 180.0,
        "outflow_rate": 30.0,
        "avg_pedestrian_speed": 0.40,
        "direction_conflict_score": 0.60,
        "gate_capacity_utilization": 0.90,
        "recent_incident_count_10min": 2,
        "reverse_flow_ratio": 0.40,
        "blockage_score": 0.50
    }

    risk_norm = predict_risk(low_density_features)
    risk_cong = predict_risk(congested_features)

    # Congested risk must be higher than normal risk
    assert risk_cong["current_risk"] > risk_norm["current_risk"]
    # Projected 5-min risk must reflect ingress accumulation momentum
    assert risk_cong["risk_5min"] >= risk_cong["current_risk"]
    db.close()


def test_edge_case_zero_citizen_gps_app_users():
    """
    EDGE CASE 3: Zero Citizen App users in zone (low adoption or GPS signal loss).
    Verifies density estimation relies on optical CCTV without division by zero.
    """
    db = SessionLocal()
    hybrid = HybridCCTVGPSIngestion()
    zone_id = "aa111111-0000-0000-0000-000000000001"

    hybrid.update_camera_telemetry(zone_id, {
        "density_peds_m2": 3.0,
        "inflow_peds_min": 140.0,
        "outflow_peds_min": 40.0,
        "avg_speed_ms": 0.40,
        "active_cameras": 4,
        "total_cameras": 4
    })

    # Execute feature extraction with zero GPS users
    features = hybrid.get_zone_features(zone_id, db)
    assert features["current_density"] == 0.75  # 3.0 peds/m2 / 4.0 = 0.75 ratio
    assert features["current_density"] > 0.0
    db.close()


def test_edge_case_conflicting_sensors_safety_first():
    """
    EDGE CASE 4: Conflicting signals (CCTV reads heavy crowd density 3.2 peds/m², but GPS count is 0).
    Verifies safety-first max() logic prioritizes the higher density reading.
    """
    db = SessionLocal()
    hybrid = HybridCCTVGPSIngestion()
    zone_id = "aa111111-0000-0000-0000-000000000001"

    hybrid.update_camera_telemetry(zone_id, {
        "density_peds_m2": 3.2,
        "inflow_peds_min": 150.0,
        "outflow_peds_min": 30.0,
        "avg_speed_ms": 0.35,
        "active_cameras": 4,
        "total_cameras": 4
    })

    features = hybrid.get_zone_features(zone_id, db)
    # Density must NOT be zeroed out by the missing GPS signal
    assert features["current_density"] >= 0.80
    risk = predict_risk(features)
    assert risk["current_risk"] >= 65.0  # High risk flag must be raised
    db.close()
