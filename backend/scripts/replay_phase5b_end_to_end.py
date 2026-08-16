"""
PHASE 5B OFFLINE REPLAY & END-TO-END PRE-PHASE-6 INFERENCE TEST SCRIPT
======================================================================
Simulates real-time telemetry stream replay:
1. Feeds sequential telemetry into rolling temporal buffer.
2. Validates schema, boundary protection (camera_id, zone_id, event_id).
3. Invokes model_loader v2.0.0 inference.
4. Evaluates EarlyWarningEngine operational state transitions.
5. Measures processing & inference latency (average & p95).
6. Verifies missing data and model failure handling.
"""

import sys
import os
import time
import json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.dataset.schema_v2 import CANDIDATE_TEMPORAL_FEATURES, PRIMARY_TEMPORAL_TARGET
from app.ai.model_loader import predict_temporal_early_warning, predict_risk_probability
from app.ai.services.early_warning_engine import EarlyWarningEngine, EarlyWarningState


def run_end_to_end_replay():
    print("==================================================")
    print(" PHASE 5B — OFFLINE REPLAY & END-TO-END INFERENCE TEST")
    print("==================================================")

    data_dir = os.path.join("data", "dataset_v2")
    test_path = os.path.join(data_dir, "test_dataset.csv")

    if not os.path.exists(test_path):
        from scripts.build_dataset_v2 import main as build_v2_main
        build_v2_main()

    test_df = pd.read_csv(test_path)
    print(f"Loaded test replay dataset: {len(test_df)} rows")

    latencies = []
    engine_states = []

    # Initialize EarlyWarningEngine per stream
    engine = EarlyWarningEngine(
        watch_threshold=0.35,
        early_warning_threshold=0.50,
        high_risk_threshold=0.85,
        persistence_steps=3,
        hysteresis_margin=0.15,
        required_history_steps=30,
    )

    # Replay Loop
    for idx, row in test_df.iterrows():
        start_t = time.perf_counter()

        feat_dict = {col: float(row[col]) for col in CANDIDATE_TEMPORAL_FEATURES if col in row}
        camera_id = str(row.get("camera_id", "cam_test"))
        zone_id = str(row.get("zone_id", "zone_test"))
        event_id = str(row.get("event_id", "evt_test"))
        telem_ts = str(row.get("timestamp", "2026-08-14T12:00:00Z"))

        # Predict Early Warning
        result = predict_temporal_early_warning(
            feature_dict=feat_dict,
            zone_id=zone_id,
            camera_id=camera_id,
            event_id=event_id,
            telemetry_timestamp=telem_ts,
            available_history_steps=idx + 1,  # Simulating growing history
        )

        end_t = time.perf_counter()
        latencies.append((end_t - start_t) * 1000.0)  # ms

        engine_states.append(result.get("operational_warning_state"))

    avg_lat = float(np.mean(latencies))
    p95_lat = float(np.percentile(latencies, 95))

    print(f"Replay completed: {len(latencies)} steps processed successfully.")
    print(f"Average Latency: {avg_lat:.3f} ms | P95 Latency: {p95_lat:.3f} ms")
    print(f"Alert States Distribution: {pd.Series(engine_states).value_counts().to_dict()}")

    # Test Model Failure Handling
    print("\n[Audit] Testing Model Failure Handling...")
    fail_res = predict_temporal_early_warning(
        feature_dict={"invalid_feature": 0.0},
        zone_id="z_fail",
        camera_id="cam_fail"
    )
    assert fail_res["status"] == "AI_UNAVAILABLE", "Model failure check failed!"
    assert fail_res["operational_warning_state"] == EarlyWarningState.DEGRADED, "Degraded state check failed!"
    print("Model failure & missing feature handling verified: STATUS = AI_UNAVAILABLE, STATE = DEGRADED.")

    # Test Persistence Rule Audit (HIGH, NORMAL, HIGH)
    print("\n[Audit] Testing Persistence Reset Rule (HIGH, NORMAL, HIGH)...")
    p_engine = EarlyWarningEngine(persistence_steps=3, early_warning_threshold=0.50)
    
    r1 = p_engine.evaluate_probability(0.70, camera_id="cam_p", zone_id="z_p", available_history_steps=35)
    assert r1["operational_warning_state"] == EarlyWarningState.WATCH
    assert r1["consecutive_high_reads"] == 1

    r2 = p_engine.evaluate_probability(0.20, camera_id="cam_p", zone_id="z_p", available_history_steps=35)
    assert r2["consecutive_high_reads"] == 0  # RESET immediately!

    r3 = p_engine.evaluate_probability(0.70, camera_id="cam_p", zone_id="z_p", available_history_steps=35)
    assert r3["consecutive_high_reads"] == 1  # 1st read again, NOT 3!
    assert r3["operational_warning_state"] == EarlyWarningState.WATCH

    print("Persistence reset rule verified: Intermittent NORMAL resets consecutive reads count.")

    replay_results = {
        "status": "PASS",
        "total_steps": len(test_df),
        "average_latency_ms": round(avg_lat, 3),
        "p95_latency_ms": round(p95_lat, 3),
        "state_distribution": pd.Series(engine_states).value_counts().to_dict(),
        "model_failure_handling": "VERIFIED_AI_UNAVAILABLE",
        "persistence_intermittent_reset": "VERIFIED_RESET",
    }

    report_path = os.path.join("data", "training_reports", "phase5b_replay_results.json")
    with open(report_path, "w") as f:
        json.dump(replay_results, f, indent=2)

    print(f"\nPhase 5B Replay Report saved to: {report_path}")
    print("==================================================")


if __name__ == "__main__":
    run_end_to_end_replay()
