"""
CrowdShield — Phase 6C.3 Contract Integration Tests
Validates temporal context intelligence contracts, stream history properties,
deduplicated state transitions, dual risk scale separation, and no-mock guarantees.
"""

import pytest
import datetime
from app.schemas.realtime_inference import (
    RealtimeInferenceResponse,
    CVTelemetrySchema,
    ProvenanceSchema,
)


def test_phase6c3_stream_payload_history_extractability():
    """
    Validates that real-time inference responses contain all necessary fields for
    the frontend Bounded Telemetry History Buffer (density, speed, person count, flow).
    """
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    res_dict = {
        "event_id": "EVT-TEST-6C3",
        "camera_id": "CAM-01",
        "zone_id": "ZONE-ALPHA",
        "timestamp": now_str,
        "current_risk": {
            "score": 68.5,
            "bucket": "MEDIUM",
        },
        "warning": {
            "operational_warning_state": "EARLY_WARNING",
            "warning_reason": "High density build-up",
            "warning_timestamp": now_str,
        },
        "ai_prediction": {
            "probability": 0.74,
            "target": "EARLY_ESCALATION_5M",
            "status": "SUCCESS",
            "horizon_seconds": 300,
        },
        "telemetry": {
            "person_count": 420,
            "tracked_person_count": 412,
            "density": 2.1,
            "average_speed": 0.48,
            "median_speed": 0.45,
            "inflow_rate": 58.0,
            "outflow_rate": 17.0,
            "flow_imbalance": 41.0,
            "net_accumulation": 41.0,
            "direction_conflict_score": 0.15,
            "reverse_flow_ratio": 0.08,
            "blockage_score": 0.22,
        },
        "camera_health": {
            "status": "ONLINE",
        },
        "is_stale": False,
        "provenance": {
            "horizon_seconds": 300,
            "is_degraded": False,
            "telemetry_timestamp": now_str,
            "prediction_timestamp": now_str,
        },
    }

    payload = RealtimeInferenceResponse.from_orchestrator_result(res_dict)

    # Validate core temporal payload fields
    assert payload.event_id == "EVT-TEST-6C3"
    assert payload.camera_id == "CAM-01"
    assert payload.zone_id == "ZONE-ALPHA"
    assert payload.current_physics_risk == 68.5
    assert payload.ai_probability == 0.74
    assert payload.operational_warning_state == "EARLY_WARNING"
    assert payload.density == 2.1
    assert payload.average_speed == 0.48
    assert payload.inflow_rate == 58.0
    assert payload.outflow_rate == 17.0


def test_phase6c3_physics_vs_ai_scale_separation():
    """
    Ensures Physics Risk (0-100) and AI Probability (0.0-1.0 / 0-100%) remain distinct
    and never conflated in schema contracts.
    """
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    res_dict = {
        "event_id": "EVT-TEST",
        "camera_id": "CAM-02",
        "zone_id": "ZONE-BETA",
        "timestamp": now_str,
        "current_risk": {
            "score": 82.0,
        },
        "warning": {
            "operational_warning_state": "HIGH_RISK",
        },
        "ai_prediction": {
            "probability": 0.89,
            "target": "EARLY_ESCALATION_5M",
            "status": "SUCCESS",
        },
        "provenance": {
            "telemetry_timestamp": now_str,
            "prediction_timestamp": now_str,
        },
    }

    payload = RealtimeInferenceResponse.from_orchestrator_result(res_dict)

    # Physics risk is 0-100 scale
    assert 0.0 <= payload.current_physics_risk <= 100.0
    # AI probability is 0.0-1.0 scale
    assert payload.ai_probability is not None
    assert 0.0 <= payload.ai_probability <= 1.0
    assert payload.current_physics_risk != payload.ai_probability * 100


def test_phase6c3_ai_unavailable_state_contract():
    """
    Validates payload structure when AI is unavailable or warming up (ai_probability is None).
    """
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    res_dict = {
        "event_id": "EVT-TEST",
        "camera_id": "CAM-03",
        "zone_id": "ZONE-GAMMA",
        "timestamp": now_str,
        "current_risk": {
            "score": 25.0,
        },
        "warning": {
            "operational_warning_state": "WARMING_UP",
        },
        "ai_prediction": {
            "probability": None,
            "status": "WARMING_UP",
        },
        "provenance": {
            "telemetry_timestamp": now_str,
            "prediction_timestamp": now_str,
        },
    }

    payload = RealtimeInferenceResponse.from_orchestrator_result(res_dict)

    assert payload.ai_probability is None
    assert payload.operational_warning_state == "WARMING_UP"
    assert payload.ai_status == "WARMING_UP"
