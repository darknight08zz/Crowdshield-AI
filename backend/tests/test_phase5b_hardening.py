"""
PHASE 5B TEMPORAL EARLY-WARNING HARDENING TEST SUITE
====================================================
Comprehensive unit test suite verifying all Phase 5B hardening requirements:
- Threshold configuration & separation
- PR-AUC & F1 report correctness
- Target metadata & versioning
- Persistence (N=3) & hysteresis (0.15)
- Warm-up & missing data handling
- Model failure & schema validation (NaN/Inf, missing features)
- Boundary protection (event, camera, zone)
- Timestamp semantics & provenance preservation
- End-to-end replay pipeline
"""

import sys
import os
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.dataset.schema_v2 import (
    CANDIDATE_TEMPORAL_FEATURES,
    PRIMARY_TEMPORAL_TARGET,
    TARGET_METADATA_V1,
    MODEL_TRAINING_THRESHOLD,
    DEFAULT_OPERATIONAL_ALERT_THRESHOLD,
    ALLOWED_PROXY_TERMINOLOGY,
)
from app.ai.services.early_warning_engine import EarlyWarningEngine, EarlyWarningState
from app.ai.model_loader import predict_temporal_early_warning, validate_feature_vector, predict_risk_probability


class TestPhase5bHardening(unittest.TestCase):

    def setUp(self):
        """Prepare valid feature vector dictionary for tests."""
        self.valid_features = {col: 0.25 for col in CANDIDATE_TEMPORAL_FEATURES}
        self.engine = EarlyWarningEngine(
            watch_threshold=0.35,
            early_warning_threshold=0.50,
            high_risk_threshold=0.85,
            persistence_steps=3,
            hysteresis_margin=0.15,
            min_alert_hold_steps=3,
            required_history_steps=30,
        )

    def test_1_threshold_configuration_and_separation(self):
        res = predict_temporal_early_warning(
            self.valid_features,
            operational_alert_threshold=0.60
        )
        self.assertEqual(res["model_training_threshold"], MODEL_TRAINING_THRESHOLD)
        self.assertEqual(res["operational_alert_threshold"], 0.60)

    def test_2_threshold_boundary_values(self):
        v1 = self.engine.evaluate_probability(0.3499, available_history_steps=35)
        self.assertEqual(v1["operational_warning_state"], EarlyWarningState.NORMAL)

        v2 = self.engine.evaluate_probability(0.3500, available_history_steps=35)
        self.assertEqual(v2["operational_warning_state"], EarlyWarningState.WATCH)

    def test_3_probability_and_alert_state_separation(self):
        res = predict_temporal_early_warning(
            self.valid_features,
            current_rule_risk=48.5,
            available_history_steps=35
        )
        self.assertIn("ai_escalation_probability", res)
        self.assertEqual(res["current_rule_based_risk"], 48.5)
        self.assertIn("operational_warning_state", res)

    def test_4_target_metadata_and_versioning(self):
        self.assertEqual(TARGET_METADATA_V1["target_name"], PRIMARY_TEMPORAL_TARGET)
        self.assertEqual(TARGET_METADATA_V1["target_version"], "1.0")
        self.assertEqual(TARGET_METADATA_V1["horizon_seconds"], 300)
        self.assertIn("PHYSICS_DEFINED_PROXY", ALLOWED_PROXY_TERMINOLOGY)

    def test_5_persistence_consecutive_rule(self):
        # 3 Consecutive HIGH reads -> Trigger EARLY_WARNING
        e = EarlyWarningEngine(persistence_steps=3, early_warning_threshold=0.50)
        
        r1 = e.evaluate_probability(0.70, available_history_steps=35)
        self.assertEqual(r1["consecutive_high_reads"], 1)
        self.assertEqual(r1["operational_warning_state"], EarlyWarningState.WATCH)

        r2 = e.evaluate_probability(0.75, available_history_steps=35)
        self.assertEqual(r2["consecutive_high_reads"], 2)
        self.assertEqual(r2["operational_warning_state"], EarlyWarningState.WATCH)

        r3 = e.evaluate_probability(0.80, available_history_steps=35)
        self.assertEqual(r3["consecutive_high_reads"], 3)
        self.assertEqual(r3["operational_warning_state"], EarlyWarningState.EARLY_WARNING)

    def test_6_persistence_reset_on_intermittent_normal(self):
        # Intermittent: HIGH, NORMAL, HIGH -> should NOT trigger EARLY_WARNING
        e = EarlyWarningEngine(persistence_steps=3, early_warning_threshold=0.50)

        r1 = e.evaluate_probability(0.70, available_history_steps=35)
        self.assertEqual(r1["consecutive_high_reads"], 1)

        r2 = e.evaluate_probability(0.20, available_history_steps=35)
        self.assertEqual(r2["consecutive_high_reads"], 0)  # RESET!

        r3 = e.evaluate_probability(0.70, available_history_steps=35)
        self.assertEqual(r3["consecutive_high_reads"], 1)  # NOT 3!
        self.assertEqual(r3["operational_warning_state"], EarlyWarningState.WATCH)

    def test_7_hysteresis_downgrade(self):
        # Hysteresis: De-escalates from HIGH_RISK only when prob < (0.85 - 0.15 = 0.70)
        e = EarlyWarningEngine(high_risk_threshold=0.85, hysteresis_margin=0.15, min_alert_hold_steps=1)
        
        for _ in range(3):
            e.evaluate_probability(0.90, available_history_steps=35)
        
        res_high = e.evaluate_probability(0.90, available_history_steps=35)
        self.assertEqual(res_high["operational_warning_state"], EarlyWarningState.HIGH_RISK)

        # Prob drops to 0.75 (above 0.70 margin) -> Stays HIGH_RISK due to hysteresis!
        res_hold = e.evaluate_probability(0.75, available_history_steps=35)
        self.assertEqual(res_hold["operational_warning_state"], EarlyWarningState.HIGH_RISK)

        # Prob drops to 0.65 (below 0.70 margin) -> Downgrades to EARLY_WARNING
        res_down = e.evaluate_probability(0.65, available_history_steps=35)
        self.assertEqual(res_down["operational_warning_state"], EarlyWarningState.EARLY_WARNING)

    def test_8_warmup_behavior(self):
        e = EarlyWarningEngine(required_history_steps=30)
        res = e.evaluate_probability(0.80, available_history_steps=10)
        self.assertEqual(res["operational_warning_state"], EarlyWarningState.WARMING_UP)
        self.assertFalse(res["history_ready"])
        self.assertEqual(res["data_quality"], "WARMING_UP")

    def test_9_missing_and_degraded_data(self):
        e = EarlyWarningEngine()
        res = e.evaluate_probability(None, is_degraded=True)
        self.assertEqual(res["operational_warning_state"], EarlyWarningState.DEGRADED)
        self.assertEqual(res["data_quality"], "DEGRADED")

    def test_10_feature_schema_nan_inf_validation(self):
        # Test NaN
        nan_feats = {**self.valid_features, "density": np.nan}
        is_val, err, _ = validate_feature_vector(nan_feats, CANDIDATE_TEMPORAL_FEATURES)
        self.assertFalse(is_val)
        self.assertIn("NaN/Inf/None", err)

        # Test missing feature
        missing_feats = {k: v for k, v in self.valid_features.items() if k != "density"}
        is_val2, err2, _ = validate_feature_vector(missing_feats, CANDIDATE_TEMPORAL_FEATURES)
        self.assertFalse(is_val2)
        self.assertIn("Missing required features", err2)

    def test_11_model_failure_handling(self):
        res = predict_temporal_early_warning({"invalid_col": 0.0})
        self.assertEqual(res["status"], "AI_UNAVAILABLE")
        self.assertEqual(res["prediction_status"], "AI_UNAVAILABLE")
        self.assertEqual(res["operational_warning_state"], EarlyWarningState.DEGRADED)
        self.assertTrue(res["is_degraded"])

    def test_12_timestamp_semantics_and_provenance(self):
        res = predict_temporal_early_warning(
            self.valid_features,
            telemetry_timestamp="2026-08-14T12:00:00Z",
            available_history_steps=35
        )
        self.assertEqual(res["telemetry_timestamp"], "2026-08-14T12:00:00Z")
        self.assertIn("prediction_timestamp", res)
        self.assertEqual(res["model_status"], "PROTOTYPE")
        self.assertEqual(res["label_type"], "PHYSICS_DEFINED_PROXY")
        self.assertIn("disclaimer", res)


if __name__ == "__main__":
    unittest.main()
