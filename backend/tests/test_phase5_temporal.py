"""
PHASE 5 TEMPORAL EARLY-WARNING INTELLIGENCE SUITE
=================================================
Unit tests for schema_v2, temporal feature extraction, Dataset V2 builder,
early warning decision engine, and model inference interface.
"""

import sys
import os
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.dataset.schema_v2 import (
    DATASET_VERSION_V2,
    CANDIDATE_TEMPORAL_FEATURES,
    PRIMARY_TEMPORAL_TARGET,
)
from app.ai.dataset.temporal_feature_extractor import (
    compute_row_physics_risk,
    compute_phase5_targets,
    extract_temporal_derivatives_and_accelerations,
    build_temporal_sequence_samples,
)
from app.ai.dataset.builder_v2 import DatasetBuilderV2
from app.ai.services.early_warning_engine import EarlyWarningEngine, EarlyWarningState
from app.ai.model_loader import predict_temporal_early_warning


class TestPhase5Temporal(unittest.TestCase):

    def setUp(self):
        """Build sample synthetic dataframe for testing."""
        n = 100
        timestamps = pd.date_range("2026-08-14 12:00:00", periods=n, freq="10s")
        self.df = pd.DataFrame({
            "timestamp": [ts.isoformat() + "Z" for ts in timestamps],
            "camera_id": ["cam_01"] * 50 + ["cam_02"] * 50,
            "zone_id": ["zone_A"] * 50 + ["zone_B"] * 50,
            "event_id": ["evt_01"] * 100,
            "density": np.linspace(0.2, 1.2, n),
            "average_speed": np.linspace(1.5, 0.3, n),
            "median_speed": np.linspace(1.4, 0.25, n),
            "inflow_rate": np.linspace(30.0, 150.0, n),
            "outflow_rate": np.linspace(40.0, 20.0, n),
            "stationary_ratio": np.linspace(0.05, 0.4, n),
            "reverse_flow_ratio": np.linspace(0.02, 0.3, n),
            "direction_conflict_score": np.linspace(0.0, 0.5, n),
            "blockage_score": np.linspace(0.0, 0.4, n),
            "person_count": np.linspace(20, 100, n).astype(int),
            "tracked_person_count": np.linspace(18, 95, n).astype(int),
            "telemetry_source": ["MIXED_EXPLICIT"] * n,
        })

    def test_schema_v2(self):
        self.assertEqual(DATASET_VERSION_V2, "v2.0")
        self.assertIn("density_acceleration", CANDIDATE_TEMPORAL_FEATURES)
        self.assertEqual(PRIMARY_TEMPORAL_TARGET, "EARLY_ESCALATION_5M")

    def test_temporal_feature_extractor(self):
        df_ext = extract_temporal_derivatives_and_accelerations(self.df)
        self.assertIn("density_change", df_ext.columns)
        self.assertIn("density_acceleration", df_ext.columns)
        self.assertIn("speed_acceleration", df_ext.columns)
        self.assertIn("rolling_density_mean", df_ext.columns)

    def test_phase5_targets_computation(self):
        df_ext = extract_temporal_derivatives_and_accelerations(self.df)
        df_targets = compute_phase5_targets(df_ext, horizon_steps=10)
        self.assertIn("RISK_DELTA_5M", df_targets.columns)
        self.assertIn("EARLY_ESCALATION_5M", df_targets.columns)

    def test_sequence_builder_boundary_protection(self):
        df_ext = extract_temporal_derivatives_and_accelerations(self.df)
        df_targets = compute_phase5_targets(df_ext, horizon_steps=10)
        clean_df = df_targets.dropna(subset=["EARLY_ESCALATION_5M"]).reset_index(drop=True)

        X_seq, y_seq, meta = build_temporal_sequence_samples(
            clean_df, sequence_length=15, feature_cols=CANDIDATE_TEMPORAL_FEATURES
        )
        self.assertEqual(X_seq.ndim, 3)
        self.assertEqual(X_seq.shape[1], 15)
        self.assertEqual(X_seq.shape[2], len(CANDIDATE_TEMPORAL_FEATURES))

    def test_early_warning_engine_stability(self):
        engine = EarlyWarningEngine(
            watch_threshold=0.35,
            early_warning_threshold=0.60,
            high_risk_threshold=0.85,
            persistence_steps=3,
        )

        # Single high reading should NOT immediately trigger EARLY_WARNING (persistence = 3)
        r1 = engine.evaluate_probability(0.70, camera_id="cam_test", zone_id="z_test", available_history_steps=35)
        self.assertEqual(r1["operational_warning_state"], EarlyWarningState.WATCH)

        # 2nd high reading
        r2 = engine.evaluate_probability(0.75, camera_id="cam_test", zone_id="z_test", available_history_steps=35)
        self.assertEqual(r2["operational_warning_state"], EarlyWarningState.WATCH)

        # 3rd high reading -> Persistence satisfied! Upgrades to EARLY_WARNING
        r3 = engine.evaluate_probability(0.80, camera_id="cam_test", zone_id="z_test", available_history_steps=35)
        self.assertEqual(r3["operational_warning_state"], EarlyWarningState.EARLY_WARNING)

    def test_model_loader_temporal_interface(self):
        dummy_feats = {col: 0.5 for col in CANDIDATE_TEMPORAL_FEATURES}
        result = predict_temporal_early_warning(dummy_feats, zone_id="zone_A", camera_id="cam_01", available_history_steps=35)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["ground_truth_status"], "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED")
        self.assertIn("operational_warning_state", result)


if __name__ == "__main__":
    unittest.main()
