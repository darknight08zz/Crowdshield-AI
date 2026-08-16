"""
CROWDSHIELD REAL-TIME AI INFERENCE ORCHESTRATOR (PHASE 6A)
==========================================================
Unified real-time inference orchestration pipeline connecting Phase 2-5 components:
1. Ingests raw video frames/telemetry & maintains in-memory rolling window buffer per stream.
2. Evaluates CameraHealthTracker operational state (ONLINE, DEGRADED, OFFLINE, CV_UNAVAILABLE).
3. Evaluates Phase 3 ground truth physics risk score (0-100 scale & LOW/MODERATE/HIGH/CRITICAL).
4. Extracts 1st/2nd order temporal derivatives & rolling acceleration features (Phase 5).
5. Evaluates Phase 5 temporal early-warning prediction (v2.0.0).
6. Evaluates EarlyWarningEngine operational alert policy (N=3 persistence, 0.15 hysteresis).
7. Returns unified inference result with explicit provenance metadata and timestamp semantics.
8. Isolates camera errors and enforces bounded memory storage.
"""

import time
import logging
import threading
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

from app.ingestion.cv.pipeline import CVPipelineManager
from app.ingestion.cv.camera_health import CameraHealthTracker
from app.ai.dataset.schema_v2 import (
    CANDIDATE_TEMPORAL_FEATURES,
    PRIMARY_TEMPORAL_TARGET,
    TARGET_METADATA_V1,
    MODEL_TRAINING_THRESHOLD,
    DEFAULT_OPERATIONAL_ALERT_THRESHOLD,
)
from app.ai.dataset.temporal_feature_extractor import (
    compute_row_physics_risk,
    extract_temporal_derivatives_and_accelerations,
)
from app.core.risk_levels import get_risk_bucket, RiskBucket
from app.ai.model_loader import predict_temporal_early_warning, load_registered_model
from app.ai.services.early_warning_engine import EarlyWarningEngine, EarlyWarningState

logger = logging.getLogger("crowdshield.ai.orchestrator")


class RealtimeInferenceResult:
    """Canonical Phase 6A Inference Result Container & Formatter."""

    @staticmethod
    def create(
        timestamp: str,
        event_id: str,
        camera_id: str,
        zone_id: str,
        camera_health: Dict[str, Any],
        telemetry: Dict[str, Any],
        current_risk: Dict[str, Any],
        ai_prediction: Dict[str, Any],
        warning: Dict[str, Any],
        provenance: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "timestamp": timestamp,
            "event_id": event_id,
            "camera_id": camera_id,
            "zone_id": zone_id,
            "camera_health": camera_health,
            "telemetry": telemetry,
            "current_risk": current_risk,
            "ai_prediction": ai_prediction,
            "warning": warning,
            "provenance": provenance,
        }


class RealtimeInferenceOrchestrator:
    """
    Thread-safe Real-Time Inference Orchestrator.
    Coordinates Phase 2 CV ingestion, Phase 3 physics risk evaluation,
    Phase 5 temporal feature extraction, v2.0.0 inference, and EarlyWarningEngine alert stability.
    """

    def __init__(
        self,
        required_history_steps: int = 30,
        max_buffer_capacity: int = 60,
        operational_alert_threshold: float = DEFAULT_OPERATIONAL_ALERT_THRESHOLD,
        persistence_steps: int = 3,
        hysteresis_margin: float = 0.15,
    ):
        self.required_history_steps = required_history_steps
        self.max_buffer_capacity = max_buffer_capacity
        self.operational_alert_threshold = operational_alert_threshold
        self.persistence_steps = persistence_steps
        self.hysteresis_margin = hysteresis_margin

        self._lock = threading.Lock()
        # Stream buffers: (event_id, camera_id, zone_id) -> List[Dict[str, Any]]
        self._stream_buffers: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
        # CV Pipelines: (camera_id, zone_id) -> CVPipelineManager
        self._cv_pipelines: Dict[Tuple[str, str], CVPipelineManager] = {}

    def _get_cv_pipeline(self, camera_id: str, zone_id: str, processing_mode: str = "LIVE") -> CVPipelineManager:
        key = (camera_id, zone_id)
        if key not in self._cv_pipelines:
            self._cv_pipelines[key] = CVPipelineManager(
                camera_id=camera_id,
                zone_id=zone_id,
                processing_mode=processing_mode
            )
        return self._cv_pipelines[key]

    def clear_stream_buffer(self, event_id: str = "default", camera_id: str = "default", zone_id: str = "default"):
        """Cleans up temporal buffer for a specific stream."""
        with self._lock:
            key = (event_id, camera_id, zone_id)
            if key in self._stream_buffers:
                del self._stream_buffers[key]

    def process_frame(
        self,
        raw_frame_or_telemetry: Any,
        camera_id: str = "CAM-01",
        zone_id: str = "zone_A",
        event_id: str = "evt_01",
        timestamp: Optional[float] = None,
        frame_id: Optional[int] = None,
        processing_mode: str = "LIVE",
        is_calibrated: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes unified real-time backend inference step for a frame or telemetry record.
        Isolated per stream key (event_id, camera_id, zone_id).
        """
        start_time = time.perf_counter()
        now_ts = timestamp if timestamp is not None else time.time()
        iso_timestamp = datetime.fromtimestamp(now_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 1. Camera Health Evaluation
        health_record = CameraHealthTracker.get_or_create(camera_id=camera_id, zone_id=zone_id)
        health_info = health_record.evaluate_health(is_calibrated=is_calibrated)

        if health_info["status"] == "OFFLINE":
            logger.warning(f"[ORCHESTRATOR] Camera '{camera_id}' is OFFLINE. Skipping inference.")
            return RealtimeInferenceResult.create(
                timestamp=iso_timestamp,
                event_id=event_id,
                camera_id=camera_id,
                zone_id=zone_id,
                camera_health=health_info,
                telemetry={},
                current_risk={"status": "OFFLINE", "score": None, "bucket": "UNKNOWN"},
                ai_prediction={"status": "CAMERA_OFFLINE", "probability": None, "history_ready": False},
                warning={"operational_warning_state": EarlyWarningState.DEGRADED, "warning_timestamp": None},
                provenance={"is_degraded": True, "reason": health_info["degradation_reason"]},
            )

        # 2. CV Perception & Telemetry Generation (Phase 2)
        t_cv0 = time.perf_counter()
        pipeline = self._get_cv_pipeline(camera_id=camera_id, zone_id=zone_id, processing_mode=processing_mode)
        try:
            if isinstance(raw_frame_or_telemetry, dict) and "density" in raw_frame_or_telemetry:
                # Pre-extracted telemetry record passed
                telemetry = {**raw_frame_or_telemetry, "timestamp": iso_timestamp, "camera_id": camera_id, "zone_id": zone_id}
                health_record.record_frame(processed=True, detection_success=True)
            else:
                # Raw image frame passed
                telemetry = pipeline.process_frame(raw_frame_or_telemetry, timestamp=now_ts, frame_id=frame_id)
                health_record.record_frame(processed=True, detection_success=True)
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] CV Pipeline failed for '{camera_id}': {e}", exc_info=True)
            health_record.record_frame(processed=True, detection_success=False)
            health_info = health_record.evaluate_health(is_calibrated=is_calibrated)
            return RealtimeInferenceResult.create(
                timestamp=iso_timestamp,
                event_id=event_id,
                camera_id=camera_id,
                zone_id=zone_id,
                camera_health=health_info,
                telemetry={},
                current_risk={"status": "CV_UNAVAILABLE", "score": None, "bucket": "UNKNOWN"},
                ai_prediction={"status": "AI_UNAVAILABLE", "probability": None, "history_ready": False},
                warning={"operational_warning_state": EarlyWarningState.DEGRADED, "warning_timestamp": None},
                provenance={"is_degraded": True, "reason": f"CV processing failure: {e}"},
            )
        t_cv1 = time.perf_counter()
        cv_perception_ms = (t_cv1 - t_cv0) * 1000.0

        # Ensure telemetry contains identifiers
        telemetry["event_id"] = event_id
        telemetry["camera_id"] = camera_id
        telemetry["zone_id"] = zone_id

        # 3. Phase 3 Ground Truth Physics Risk Evaluation
        t_phys0 = time.perf_counter()
        telemetry_series = pd.Series(telemetry)
        physics_risk_score = compute_row_physics_risk(telemetry_series)
        risk_bucket = get_risk_bucket(physics_risk_score)
        current_risk_payload = {
            "score": round(physics_risk_score, 1),
            "bucket": risk_bucket.value,
            "status": "SUCCESS",
            "formula_type": "PHYSICS_DETERMINISTIC_GROUND_TRUTH",
        }
        t_phys1 = time.perf_counter()
        physics_risk_ms = (t_phys1 - t_phys0) * 1000.0

        # 4. Stream Buffer Ingestion (Bounded Memory)
        stream_key = (event_id, camera_id, zone_id)
        with self._lock:
            if stream_key not in self._stream_buffers:
                self._stream_buffers[stream_key] = []
            
            buf = self._stream_buffers[stream_key]
            buf.append(telemetry)
            if len(buf) > self.max_buffer_capacity:
                buf.pop(0)
            
            history_len = len(buf)
            buf_snapshot = list(buf)

        # 5. Check Warm-Up Status
        if history_len < self.required_history_steps:
            logger.debug(f"[ORCHESTRATOR] Warm-up phase ({history_len}/{self.required_history_steps}) for {stream_key}")
            total_lat_ms = (time.perf_counter() - start_time) * 1000.0
            stage_breakdown = {
                "cv_perception_ms": round(cv_perception_ms, 2),
                "physics_risk_ms": round(physics_risk_ms, 2),
                "temporal_feature_extraction_ms": 0.0,
                "ai_inference_ms": 0.0,
                "total_orchestration_latency_ms": round(total_lat_ms, 2),
            }
            if "stage_timing" in telemetry and isinstance(telemetry["stage_timing"], dict):
                stage_breakdown.update(telemetry["stage_timing"])
            return RealtimeInferenceResult.create(
                timestamp=iso_timestamp,
                event_id=event_id,
                camera_id=camera_id,
                zone_id=zone_id,
                camera_health=health_info,
                telemetry=telemetry,
                current_risk=current_risk_payload,
                ai_prediction={
                    "status": "WARMING_UP",
                    "prediction_status": "WARMING_UP",
                    "model_version": "v2.0.0",
                    "target": PRIMARY_TEMPORAL_TARGET,
                    "horizon_seconds": 300,
                    "probability": None,
                    "history_ready": False,
                    "available_history_steps": history_len,
                    "required_history_steps": self.required_history_steps,
                },
                warning={
                    "operational_warning_state": EarlyWarningState.WARMING_UP,
                    "raw_candidate_state": EarlyWarningState.WARMING_UP,
                    "warning_timestamp": None,
                },
                provenance={
                    "processing_mode": processing_mode,
                    "telemetry_source": telemetry.get("telemetry_source", "live_cctv_gps"),
                    "calibration_status": telemetry.get("calibration_status", "UNCALIBRATED"),
                    "model_status": "PROTOTYPE",
                    "label_type": "PHYSICS_DEFINED_PROXY",
                    "ground_truth_status": "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
                    "is_degraded": telemetry.get("is_degraded", False),
                    "is_synthetic": (processing_mode == "SIMULATION"),
                    "is_simulated": (processing_mode == "SIMULATION"),
                    "stage_breakdown_ms": stage_breakdown,
                    "total_orchestration_latency_ms": round(total_lat_ms, 3),
                    "disclaimer": "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.",
                },
            )

        # 6. Temporal Feature Extraction (Phase 5)
        t_fe0 = time.perf_counter()
        feature_window_start = buf_snapshot[0].get("timestamp", iso_timestamp)
        feature_window_end = buf_snapshot[-1].get("timestamp", iso_timestamp)

        try:
            history_df = pd.DataFrame(buf_snapshot)
            history_ext = extract_temporal_derivatives_and_accelerations(history_df)
            latest_row = history_ext.iloc[-1]

            feat_dict = {}
            for col in CANDIDATE_TEMPORAL_FEATURES:
                feat_dict[col] = float(latest_row.get(col, 0.0))
            t_fe1 = time.perf_counter()
            temporal_extraction_ms = (t_fe1 - t_fe0) * 1000.0

            # 7. AI Model Inference & Early Warning Engine Evaluation
            t_ai0 = time.perf_counter()
            ai_res = predict_temporal_early_warning(
                feature_dict=feat_dict,
                zone_id=zone_id,
                camera_id=camera_id,
                event_id=event_id,
                current_rule_risk=physics_risk_score,
                telemetry_timestamp=iso_timestamp,
                operational_alert_threshold=self.operational_alert_threshold,
                available_history_steps=history_len,
            )
            t_ai1 = time.perf_counter()
            ai_inference_ms = (t_ai1 - t_ai0) * 1000.0

        except Exception as e:
            logger.error(f"[ORCHESTRATOR] AI Inference failed for {stream_key}: {e}", exc_info=True)
            t_fe1 = time.perf_counter()
            temporal_extraction_ms = (t_fe1 - t_fe0) * 1000.0
            ai_inference_ms = 0.0
            ai_res = {
                "status": "AI_UNAVAILABLE",
                "prediction_status": "AI_UNAVAILABLE",
                "model_version": "v2.0.0",
                "target": PRIMARY_TEMPORAL_TARGET,
                "horizon_seconds": 300,
                "ai_escalation_probability": None,
                "operational_warning_state": EarlyWarningState.DEGRADED,
                "raw_candidate_state": EarlyWarningState.DEGRADED,
                "is_degraded": True,
                "warning_timestamp": None,
            }

        total_lat_ms = (time.perf_counter() - start_time) * 1000.0

        ai_prediction_payload = {
            "status": ai_res.get("status", "SUCCESS"),
            "prediction_status": ai_res.get("prediction_status", "SUCCESS"),
            "model_version": ai_res.get("model_version", "v2.0.0"),
            "target": ai_res.get("target", PRIMARY_TEMPORAL_TARGET),
            "target_metadata": TARGET_METADATA_V1,
            "horizon_seconds": ai_res.get("horizon_seconds", 300),
            "probability": ai_res.get("ai_escalation_probability"),
            "model_training_threshold": ai_res.get("model_training_threshold", MODEL_TRAINING_THRESHOLD),
            "operational_alert_threshold": self.operational_alert_threshold,
            "history_ready": True,
            "available_history_steps": history_len,
            "explainability": ai_res.get("explainability", {}),
        }

        warning_payload = {
            "operational_warning_state": ai_res.get("operational_warning_state", EarlyWarningState.NORMAL),
            "raw_candidate_state": ai_res.get("raw_candidate_state", EarlyWarningState.NORMAL),
            "warning_timestamp": ai_res.get("warning_timestamp"),
        }

        stage_breakdown = {
            "cv_perception_ms": round(cv_perception_ms, 2),
            "physics_risk_ms": round(physics_risk_ms, 2),
            "temporal_feature_extraction_ms": round(temporal_extraction_ms, 2),
            "ai_inference_ms": round(ai_inference_ms, 2),
            "total_orchestration_latency_ms": round(total_lat_ms, 2),
        }
        if "stage_timing" in telemetry and isinstance(telemetry["stage_timing"], dict):
            stage_breakdown.update(telemetry["stage_timing"])

        provenance_payload = {
            "event_id": event_id,
            "camera_id": camera_id,
            "zone_id": zone_id,
            "processing_mode": processing_mode,
            "telemetry_source": telemetry.get("telemetry_source", "live_cctv_gps"),
            "calibration_status": telemetry.get("calibration_status", "UNCALIBRATED"),
            "telemetry_timestamp": iso_timestamp,
            "feature_window_start": feature_window_start,
            "feature_window_end": feature_window_end,
            "prediction_timestamp": iso_timestamp,
            "model_status": "PROTOTYPE",
            "label_type": "PHYSICS_DEFINED_PROXY",
            "ground_truth_status": "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
            "generalization_status": "INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION",
            "is_degraded": (ai_res.get("is_degraded", False) or health_info.get("is_degraded", False)),
            "is_synthetic": (processing_mode == "SIMULATION"),
            "is_simulated": (processing_mode == "SIMULATION"),
            "stage_breakdown_ms": stage_breakdown,
            "total_orchestration_latency_ms": round(total_lat_ms, 3),
            "disclaimer": "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.",
        }

        logger.debug(f"[ORCHESTRATOR] Processed frame for {stream_key} in {total_lat_ms:.2f}ms. State: {warning_payload['operational_warning_state']}")

        return RealtimeInferenceResult.create(
            timestamp=iso_timestamp,
            event_id=event_id,
            camera_id=camera_id,
            zone_id=zone_id,
            camera_health=health_info,
            telemetry=telemetry,
            current_risk=current_risk_payload,
            ai_prediction=ai_prediction_payload,
            warning=warning_payload,
            provenance=provenance_payload,
        )
