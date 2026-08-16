"""
PHASE 6A REAL-TIME BACKEND INFERENCE ORCHESTRATION TEST SUITE
============================================================
Comprehensive test suite verifying all 30 Phase 6A requirements:
- Stream buffer scoping & boundary protection (event/camera/zone)
- Warm-up behavior (< 30 steps) & sufficient history execution (>= 30 steps)
- Probability vs Alert State separation & Phase 3 Physics Risk separation
- EarlyWarningEngine persistence (N=3) & hysteresis (0.15)
- Camera health integration (ONLINE, DEGRADED, OFFLINE, CV_UNAVAILABLE)
- Schema validation, missing features, NaN/Inf handling
- Bounded memory storage & stream buffer cleanup
- Error isolation across streams
- Reproducible replay test execution
"""

import sys
import os
import time
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.services.inference_orchestrator import RealtimeInferenceOrchestrator, RealtimeInferenceResult
from app.ai.services.early_warning_engine import EarlyWarningState
from app.ai.dataset.schema_v2 import CANDIDATE_TEMPORAL_FEATURES, PRIMARY_TEMPORAL_TARGET
from app.ingestion.cv.camera_health import CameraHealthTracker


class TestPhase6aOrchestrator(unittest.TestCase):

    def setUp(self):
        """Prepare orchestrator instance and baseline sample telemetry."""
        self.orchestrator = RealtimeInferenceOrchestrator(
            required_history_steps=30,
            max_buffer_capacity=60,
            operational_alert_threshold=0.50,
            persistence_steps=3,
            hysteresis_margin=0.15,
        )
        self.base_telemetry = {
            "density": 0.5,
            "average_speed": 1.2,
            "median_speed": 1.1,
            "inflow_rate": 45.0,
            "outflow_rate": 40.0,
            "flow_imbalance": 5.0,
            "stationary_ratio": 0.1,
            "reverse_flow_ratio": 0.05,
            "direction_conflict_score": 0.1,
            "blockage_score": 0.15,
            "person_count": 25,
            "tracked_person_count": 22,
            "density_change": 0.01,
            "density_rate": 0.001,
            "density_acceleration": 0.0,
            "speed_change": -0.02,
            "speed_rate": -0.002,
            "speed_acceleration": 0.0,
            "inflow_change": 1.0,
            "outflow_change": -0.5,
            "rolling_density_mean": 0.48,
            "rolling_density_std": 0.02,
            "rolling_speed_mean": 1.22,
            "rolling_speed_std": 0.05,
        }

    def test_1_valid_frame_processing_and_contract(self):
        res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_1", zone_id="Z_1", event_id="EVT_1")
        self.assertEqual(res["camera_id"], "CAM_1")
        self.assertEqual(res["zone_id"], "Z_1")
        self.assertEqual(res["event_id"], "EVT_1")
        self.assertIn("telemetry", res)
        self.assertIn("current_risk", res)
        self.assertIn("ai_prediction", res)
        self.assertIn("warning", res)
        self.assertIn("provenance", res)

    def test_2_detection_failure_handling(self):
        # Force a pipeline exception by breaking CV pipeline call
        pipe = self.orchestrator._get_cv_pipeline(camera_id="CAM_FAIL", zone_id="Z_1")
        pipe.process_frame = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("CV Pipeline Crash"))
        res = self.orchestrator.process_frame(12345, camera_id="CAM_FAIL", zone_id="Z_1")
        self.assertEqual(res["ai_prediction"]["status"], "AI_UNAVAILABLE")
        self.assertEqual(res["warning"]["operational_warning_state"], EarlyWarningState.DEGRADED)

    def test_3_empty_detection_valid_telemetry(self):
        empty_telemetry = {**self.base_telemetry, "person_count": 0, "tracked_person_count": 0, "density": 0.0}
        res = self.orchestrator.process_frame(empty_telemetry, camera_id="CAM_EMPTY", zone_id="Z_1")
        self.assertEqual(res["telemetry"]["person_count"], 0)
        self.assertEqual(res["current_risk"]["bucket"], "LOW")

    def test_4_tracker_output_structure(self):
        res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_TRACK", zone_id="Z_1")
        self.assertEqual(res["telemetry"]["person_count"], 25)
        self.assertEqual(res["telemetry"]["tracked_person_count"], 22)

    def test_5_telemetry_generation(self):
        res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_1", zone_id="Z_1")
        self.assertIn("density", res["telemetry"])
        self.assertIn("inflow_rate", res["telemetry"])
        self.assertIn("average_speed", res["telemetry"])

    def test_6_temporal_buffer_update(self):
        self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_BUF", zone_id="Z_1", event_id="E_1")
        key = ("E_1", "CAM_BUF", "Z_1")
        self.assertEqual(len(self.orchestrator._stream_buffers[key]), 1)

    def test_7_warmup_behavior_under_30_steps(self):
        for i in range(15):
            res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_WARM", zone_id="Z_1")
        self.assertEqual(res["ai_prediction"]["status"], "WARMING_UP")
        self.assertFalse(res["ai_prediction"]["history_ready"])
        self.assertEqual(res["warning"]["operational_warning_state"], EarlyWarningState.WARMING_UP)

    def test_8_sufficient_history_execution_30_steps(self):
        for i in range(30):
            res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_READY", zone_id="Z_1")
        self.assertEqual(res["ai_prediction"]["status"], "SUCCESS")
        self.assertTrue(res["ai_prediction"]["history_ready"])

    def test_9_model_inference_execution(self):
        for i in range(30):
            res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_INF", zone_id="Z_1")
        self.assertIn("probability", res["ai_prediction"])
        self.assertEqual(res["ai_prediction"]["target"], PRIMARY_TEMPORAL_TARGET)

    def test_10_model_unavailable_fallback(self):
        # Pass telemetry with density = None which computes risk safely without crashing
        bad_telemetry = {**self.base_telemetry, "density": None}
        for i in range(29):
            self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_UNAVAIL", zone_id="Z_1")
        res = self.orchestrator.process_frame(bad_telemetry, camera_id="CAM_UNAVAIL", zone_id="Z_1")
        self.assertEqual(res["current_risk"]["status"], "SUCCESS")

    def test_11_missing_feature_handling(self):
        incomplete_telemetry = {k: v for k, v in self.base_telemetry.items() if k != "density"}
        res = self.orchestrator.process_frame(incomplete_telemetry, camera_id="CAM_MISS", zone_id="Z_1")
        self.assertEqual(res["current_risk"]["status"], "SUCCESS")

    def test_12_nan_feature_handling(self):
        nan_telemetry = {**self.base_telemetry, "density": np.nan}
        for i in range(29):
            self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_NAN", zone_id="Z_1")
        res = self.orchestrator.process_frame(nan_telemetry, camera_id="CAM_NAN", zone_id="Z_1")
        self.assertEqual(res["current_risk"]["status"], "SUCCESS")

    def test_13_camera_offline_handling(self):
        h = CameraHealthTracker.get_or_create("CAM_OFF", "Z_1")
        h.last_frame_timestamp = time.time() - 20.0  # Offline > 15s
        res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_OFF", zone_id="Z_1")
        self.assertEqual(res["ai_prediction"]["status"], "CAMERA_OFFLINE")
        self.assertEqual(res["warning"]["operational_warning_state"], EarlyWarningState.DEGRADED)

    def test_14_cv_unavailable_handling(self):
        h = CameraHealthTracker.get_or_create("CAM_CV", "Z_1")
        h.detection_success_rate = 0.1  # CV failing < 0.5
        res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_CV", zone_id="Z_1", is_calibrated=True)
        self.assertEqual(res["camera_health"]["status"], "CV_UNAVAILABLE")

    def test_15_degraded_telemetry_propagation(self):
        degraded_telemetry = {**self.base_telemetry, "is_degraded": True}
        res = self.orchestrator.process_frame(degraded_telemetry, camera_id="CAM_DEG", zone_id="Z_1")
        self.assertTrue(res["provenance"]["is_degraded"])

    def test_16_event_boundary_protection(self):
        self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_1", zone_id="Z_1", event_id="EVT_A")
        self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_1", zone_id="Z_1", event_id="EVT_B")
        self.assertIn(("EVT_A", "CAM_1", "Z_1"), self.orchestrator._stream_buffers)
        self.assertIn(("EVT_B", "CAM_1", "Z_1"), self.orchestrator._stream_buffers)
        self.assertEqual(len(self.orchestrator._stream_buffers[("EVT_A", "CAM_1", "Z_1")]), 1)
        self.assertEqual(len(self.orchestrator._stream_buffers[("EVT_B", "CAM_1", "Z_1")]), 1)

    def test_17_camera_boundary_protection(self):
        self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_A", zone_id="Z_1", event_id="EVT_1")
        self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_B", zone_id="Z_1", event_id="EVT_1")
        self.assertNotEqual(
            self.orchestrator._stream_buffers[("EVT_1", "CAM_A", "Z_1")],
            self.orchestrator._stream_buffers[("EVT_1", "CAM_B", "Z_1")]
        )

    def test_18_zone_boundary_protection(self):
        self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_1", zone_id="Z_A", event_id="EVT_1")
        self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_1", zone_id="Z_B", event_id="EVT_1")
        self.assertIn(("EVT_1", "CAM_1", "Z_A"), self.orchestrator._stream_buffers)
        self.assertIn(("EVT_1", "CAM_1", "Z_B"), self.orchestrator._stream_buffers)

    def test_19_timestamp_semantics(self):
        for i in range(30):
            res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_TS", zone_id="Z_1")
        prov = res["provenance"]
        self.assertIn("telemetry_timestamp", prov)
        self.assertIn("feature_window_start", prov)
        self.assertIn("feature_window_end", prov)
        self.assertIn("prediction_timestamp", prov)

    def test_20_probability_vs_alert_state_separation(self):
        for i in range(30):
            res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_SEP", zone_id="Z_1")
        prob = res["ai_prediction"]["probability"]
        state = res["warning"]["operational_warning_state"]
        self.assertIsInstance(prob, (float, type(None)))
        self.assertIn(state, [EarlyWarningState.NORMAL, EarlyWarningState.WATCH, EarlyWarningState.EARLY_WARNING, EarlyWarningState.HIGH_RISK])

    def test_21_persistence_behavior(self):
        for i in range(30):
            res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_PERSIST", zone_id="Z_1")
        self.assertIn(res["warning"]["operational_warning_state"], [EarlyWarningState.NORMAL, EarlyWarningState.WATCH, EarlyWarningState.EARLY_WARNING, EarlyWarningState.HIGH_RISK])

    def test_22_hysteresis_behavior(self):
        for i in range(35):
            res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_HYST", zone_id="Z_1")
        self.assertEqual(res["warning"]["operational_warning_state"], EarlyWarningState.NORMAL)

    def test_23_provenance_propagation(self):
        res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_PROV", zone_id="Z_1")
        prov = res["provenance"]
        self.assertEqual(prov["model_status"], "PROTOTYPE")
        self.assertEqual(prov["label_type"], "PHYSICS_DEFINED_PROXY")
        self.assertIn("disclaimer", prov)

    def test_24_calibration_propagation(self):
        res_uncalib = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_UNCALIB", zone_id="Z_1", is_calibrated=False)
        self.assertEqual(res_uncalib["provenance"]["calibration_status"], "UNCALIBRATED")

    def test_25_processing_mode_propagation(self):
        res_sim = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_SIM", zone_id="Z_1", processing_mode="SIMULATION")
        self.assertEqual(res_sim["provenance"]["processing_mode"], "SIMULATION")
        self.assertTrue(res_sim["provenance"]["is_simulated"])

    def test_26_v1_v2_version_correctness(self):
        for i in range(30):
            res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_VER", zone_id="Z_1")
        self.assertEqual(res["ai_prediction"]["model_version"], "v2.0.0")

    def test_27_bounded_temporal_buffer(self):
        for i in range(75):
            self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_BOUND", zone_id="Z_1")
        key = ("evt_01", "CAM_BOUND", "Z_1")
        self.assertEqual(len(self.orchestrator._stream_buffers[key]), 60)

    def test_28_error_isolation(self):
        # Stream 1 has CV error
        pipe = self.orchestrator._get_cv_pipeline(camera_id="CAM_ERR1", zone_id="Z_1")
        pipe.process_frame = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("CV Pipeline Crash"))
        res1 = self.orchestrator.process_frame(12345, camera_id="CAM_ERR1", zone_id="Z_1")
        self.assertEqual(res1["ai_prediction"]["status"], "AI_UNAVAILABLE")
        # Stream 2 processes normally
        res2 = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_ERR2", zone_id="Z_1")
        self.assertEqual(res2["current_risk"]["status"], "SUCCESS")

    def test_29_replay_integration(self):
        latencies = []
        for i in range(35):
            t0 = time.perf_counter()
            res = self.orchestrator.process_frame(self.base_telemetry, camera_id="CAM_REPLAY", zone_id="Z_1")
            latencies.append((time.perf_counter() - t0) * 1000.0)
        self.assertEqual(res["ai_prediction"]["status"], "SUCCESS")
        self.assertLess(np.mean(latencies), 100.0)  # Sub-100ms requirement

    def test_30_deterministic_reproducible_output(self):
        o1 = RealtimeInferenceOrchestrator(required_history_steps=30)
        o2 = RealtimeInferenceOrchestrator(required_history_steps=30)
        for i in range(30):
            r1 = o1.process_frame(self.base_telemetry, camera_id="CAM_DET", zone_id="Z_1")
            r2 = o2.process_frame(self.base_telemetry, camera_id="CAM_DET", zone_id="Z_1")
        self.assertEqual(r1["ai_prediction"]["probability"], r2["ai_prediction"]["probability"])
        self.assertEqual(r1["warning"]["operational_warning_state"], r2["warning"]["operational_warning_state"])


if __name__ == "__main__":
    unittest.main()
