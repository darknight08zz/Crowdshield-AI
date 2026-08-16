"""
Phase 6C.2 Operator Dashboard Intelligence & Telemetry Contract Tests

Validates:
1. Canonical schema & field presence for all 12 telemetry metrics.
2. Distinct physics risk score vs AI early-warning probability.
3. Provenance target EARLY_ESCALATION_5M alignment & prototype disclaimer.
4. Operational warning state & camera health contract compliance.
5. Stale, degraded, and warming up payload contract behavior.
"""

import pytest
import datetime
from app.schemas.realtime_inference import RealtimeInferenceResponse

def test_phase6c2_telemetry_12_metrics_contract():
    """Verify all 12 telemetry fields are properly modeled and structured."""
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    mock_orchestrator_dict = {
        "event_id": "EVT-MAIN",
        "camera_id": "CAM-6C2",
        "zone_id": "ZONE-6C2",
        "timestamp": now_str,
        "camera_health": {"status": "ONLINE", "is_degraded": False},
        "telemetry": {
            "person_count": 1850,
            "tracked_person_count": 1820,
            "density": 2.1,
            "average_speed": 0.48,
            "median_speed": 0.45,
            "inflow_rate": 58.0,
            "outflow_rate": 17.0,
            "flow_imbalance": 41.0,
            "net_accumulation": 205.0,
            "direction_conflict_score": 0.35,
            "reverse_flow_ratio": 0.12,
            "blockage_score": 0.40,
        },
        "current_risk": {
            "score": 62.0,
            "bucket": "HIGH",
        },
        "ai_prediction": {
            "status": "SUCCESS",
            "model_version": "v2.0.0",
            "target": "EARLY_ESCALATION_5M",
            "horizon_seconds": 300,
            "probability": 0.73,
            "history_ready": True,
        },
        "warning": {
            "operational_warning_state": "EARLY_WARNING",
            "warning_reason": "High localized density and inflow imbalance",
            "persistence_count": 3,
            "warning_timestamp": now_str,
        },
        "provenance": {
            "model_status": "PROTOTYPE",
            "label_type": "PHYSICS_DEFINED_PROXY",
            "ground_truth_status": "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
            "generalization_status": "INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION",
            "disclaimer": "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.",
            "telemetry_timestamp": now_str,
            "prediction_timestamp": now_str,
        },
    }

    resp = RealtimeInferenceResponse.from_orchestrator_result(mock_orchestrator_dict)
    dump = resp.model_dump()

    # 12 Telemetry metrics assertions
    assert dump["person_count"] == 1850
    assert dump["tracked_person_count"] == 1820
    assert dump["density"] == 2.1
    assert dump["average_speed"] == 0.48
    assert dump["median_speed"] == 0.45
    assert dump["inflow_rate"] == 58.0
    assert dump["outflow_rate"] == 17.0
    assert dump["flow_imbalance"] == 41.0
    assert dump["net_accumulation"] == 205.0
    assert dump["direction_conflict_score"] == 0.35
    assert dump["reverse_flow_ratio"] == 0.12
    assert dump["blockage_score"] == 0.40

    # Physics Risk vs AI Probability separation
    assert dump["current_physics_risk"] == 62.0
    assert dump["ai_probability"] == 0.73

    # Operational state & provenance
    assert dump["operational_warning_state"] == "EARLY_WARNING"
    assert dump["target"] == "EARLY_ESCALATION_5M"
    assert dump["horizon_seconds"] == 300
    assert "not operationally validated" in dump["disclaimer"]

def test_phase6c2_warming_up_and_degraded_states():
    """Verify warming up and degraded payload behavior in contract mapper."""
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    warmup_dict = {
        "event_id": "EVT-MAIN",
        "camera_id": "CAM-WARMUP",
        "zone_id": "ZONE-WARMUP",
        "timestamp": now_str,
        "camera_health": {"status": "ONLINE"},
        "telemetry": {"density": 0.8},
        "current_risk": {"score": 25.0},
        "ai_prediction": {
            "status": "WARMING_UP",
            "probability": None,
            "history_ready": False,
        },
        "warning": {"operational_warning_state": "WARMING_UP"},
        "provenance": {"telemetry_timestamp": now_str, "prediction_timestamp": now_str},
    }

    resp_warmup = RealtimeInferenceResponse.from_orchestrator_result(warmup_dict)
    dump_warmup = resp_warmup.model_dump()
    assert dump_warmup["ai_probability"] is None
    assert dump_warmup["operational_warning_state"] == "WARMING_UP"
    assert dump_warmup["history_ready"] is False

    degraded_dict = {
        "event_id": "EVT-MAIN",
        "camera_id": "CAM-DEG",
        "zone_id": "ZONE-DEG",
        "timestamp": now_str,
        "camera_health": {"status": "DEGRADED", "is_degraded": True},
        "telemetry": {"density": 1.6},
        "current_risk": {"score": 50.0},
        "ai_prediction": {"status": "AI_UNAVAILABLE", "probability": None},
        "warning": {"operational_warning_state": "DEGRADED"},
        "provenance": {"is_degraded": True, "telemetry_timestamp": now_str, "prediction_timestamp": now_str},
    }

    resp_deg = RealtimeInferenceResponse.from_orchestrator_result(degraded_dict)
    dump_deg = resp_deg.model_dump()
    assert dump_deg["operational_warning_state"] == "DEGRADED"
    assert dump_deg["camera_health_status"] == "DEGRADED"
    assert dump_deg["is_degraded"] is True
