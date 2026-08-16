"""
CROWDSHIELD CV PIPELINE MANAGER
==============================
Consolidates Frame Sampling, Person Detection, ByteTrack Tracking, Density Estimation,
Metric Extraction, and Dynamic Strategy Selection into a unified real-time execution pipeline.

DOWNSTREAM CONTRACT & CANONICAL TELEMETRY SCHEMA:
--------------------------------------------------
Output Schema:
{
    "timestamp": str (ISO-8601 UTC),
    "camera_id": str,
    "zone_id": str,
    "density": float,
    "density_unit": "persons_per_m2" | "NORMALIZED_ESTIMATE",
    "density_confidence": float,
    "inflow_rate": float,
    "outflow_rate": float,
    "flow_imbalance": float,
    "average_speed": float,
    "median_speed": float,
    "speed_unit": "m_s" | "NORMALIZED_SPEED",
    "stationary_ratio": float,
    "reverse_flow_ratio": float,
    "direction_conflict_score": float,
    "blockage_score": float,
    "person_count": int,
    "tracked_person_count": int,
    "behavior_classification": str,
    "behavior_classifier_type": "RULE_BASED_BEHAVIOR_CLASSIFIER",
    "telemetry_source": "live_cctv_gps",
    "processing_mode": "LIVE" | "DEMO" | "SIMULATION",
    "calibration_status": "HOMOGRAPHY" | "UNCALIBRATED",
    "confidence_score": float,
    "is_degraded": bool,
    "is_synthetic": bool,
    "is_simulated": bool
}
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.ingestion.cv.frame_sampler import FrameSampler
from app.ingestion.cv.detector import PersonDetector
from app.ingestion.cv.tracker import ByteTracker
from app.ingestion.cv.density_estimator import DensityEstimator
from app.ingestion.cv.strategy import select_detection_strategy
from app.ingestion.cv.line_crossing import LineCrossingDetector
from app.ingestion.cv.flow_rate import GateFlowRateAggregator
from app.ingestion.cv.metrics import (
    calculate_density,
    calculate_speed_metrics,
    calculate_direction_and_conflict,
    calculate_blockage_score,
    classify_crowd_behavior
)

logger = logging.getLogger("crowdshield.cv.pipeline")


class CVPipelineManager:
    """
    Orchestrates computer vision pipeline execution per zone/camera.
    Processes video frames and produces canonical crowd telemetry objects.
    """

    def __init__(
        self,
        zone_id: str,
        camera_id: str = "CAM-01",
        zone_area_m2: float = 100.0,
        virtual_line: Optional[List[List[float]]] = None,
        homography_matrix: Optional[List[List[float]]] = None,
        is_calibrated: bool = False,
        processing_mode: str = "LIVE"
    ):
        self.zone_id = zone_id
        self.camera_id = camera_id
        self.zone_area_m2 = zone_area_m2
        self.homography_matrix = homography_matrix
        self.is_calibrated = is_calibrated
        self.processing_mode = processing_mode

        self.sampler = FrameSampler(target_fps=settings.FRAME_SAMPLE_RATE)
        self.detector = PersonDetector(confidence_threshold=0.35)
        self.tracker = ByteTracker(iou_threshold=0.30)
        self.density_estimator = DensityEstimator(zone_area_m2=zone_area_m2)

        self.line_detector = LineCrossingDetector(gate_id=zone_id, virtual_line=virtual_line)
        self.flow_aggregator = GateFlowRateAggregator(gate_id=zone_id)

        self.last_density_estimate = 0.50
        self.frame_counter = 0

    def process_frame(
        self,
        raw_frame_or_telemetry: Any,
        timestamp: Optional[float] = None,
        frame_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes the sampled CV pipeline step for the zone.
        Returns canonical telemetry dictionary.
        """
        now = timestamp if timestamp is not None else time.time()
        self.frame_counter += 1
        current_frame_id = frame_id or self.frame_counter

        # 1. Frame Sampling check
        should_process = self.sampler.should_process_frame(now)

        # 2. Extract preliminary density estimate to guide strategy choice
        prelim_density = self.last_density_estimate
        if isinstance(raw_frame_or_telemetry, dict):
            if "raw_density_peds_m2" in raw_frame_or_telemetry:
                prelim_density = float(raw_frame_or_telemetry["raw_density_peds_m2"])
            elif "density_peds_m2" in raw_frame_or_telemetry:
                prelim_density = float(raw_frame_or_telemetry["density_peds_m2"])
            elif "density" in raw_frame_or_telemetry:
                prelim_density = float(raw_frame_or_telemetry["density"])

        # 3. Dynamic Strategy Switch Check
        active_strategy, reason = select_detection_strategy(self.zone_id, prelim_density)

        iso_timestamp = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 4. Strategy Execution
        stage_timing = {}
        if active_strategy == "detection_tracking":
            t_det0 = time.perf_counter()
            detections = self.detector.detect_persons(
                raw_frame_or_telemetry,
                timestamp=now,
                frame_id=current_frame_id,
                processing_mode=self.processing_mode
            )
            t_det1 = time.perf_counter()
            stage_timing["yolo_inference_ms"] = round((t_det1 - t_det0) * 1000.0, 2)

            t_trk0 = time.perf_counter()
            tracks = self.tracker.update(detections, timestamp=now, frame_id=current_frame_id)
            t_trk1 = time.perf_counter()
            stage_timing["bytetrack_update_ms"] = round((t_trk1 - t_trk0) * 1000.0, 2)

            t_met0 = time.perf_counter()
            # Virtual Line Crossing & Flow Aggregation
            crossing_events = self.line_detector.process_tracks(tracks)
            for ev in crossing_events:
                self.flow_aggregator.record_crossing(ev["direction"], ev["timestamp"])

            flow_metrics = self.flow_aggregator.get_flow_rates(now)

            person_count = len(tracks) if tracks else len(detections)
            tracked_person_count = len([t for t in tracks if t.get("state") == "ACTIVE"])

            # Spatial Density & Calibration Metrics
            if isinstance(raw_frame_or_telemetry, dict) and ("density_peds_m2" in raw_frame_or_telemetry or "raw_density_peds_m2" in raw_frame_or_telemetry or "density" in raw_frame_or_telemetry):
                density_val = prelim_density
                density_unit = "persons_per_m2" if self.is_calibrated else "NORMALIZED_ESTIMATE"
                calib_status = "HOMOGRAPHY" if self.is_calibrated else "UNCALIBRATED"
            else:
                density_val, density_unit, calib_status = calculate_density(
                    person_count=person_count,
                    zone_area_m2=self.zone_area_m2,
                    homography_matrix=self.homography_matrix,
                    is_calibrated=self.is_calibrated
                )
            self.last_density_estimate = density_val

            # Speed Metrics
            speed_metrics = calculate_speed_metrics(
                tracks=tracks,
                homography_matrix=self.homography_matrix,
                is_calibrated=self.is_calibrated
            )

            # Direction & Conflict Metrics
            direction_metrics = calculate_direction_and_conflict(tracks)

            # Blockage & Flow Imbalance Metrics
            flow_imbalance = round(abs(flow_metrics["inflow_rate"] - flow_metrics["outflow_rate"]), 1)
            blockage = calculate_blockage_score(
                density_peds_m2=density_val,
                median_speed=speed_metrics["median_speed"],
                stationary_ratio=speed_metrics["stationary_ratio"],
                inflow_rate=flow_metrics["inflow_rate"],
                outflow_rate=flow_metrics["outflow_rate"]
            )

            # Rule-Based Behavior Classification
            behavior = classify_crowd_behavior(
                density_peds_m2=density_val,
                median_speed=speed_metrics["median_speed"],
                stationary_ratio=speed_metrics["stationary_ratio"],
                reverse_flow_ratio=direction_metrics["reverse_flow_ratio"],
                direction_conflict_score=direction_metrics["direction_conflict_score"],
                blockage_score=blockage,
                inflow_rate=flow_metrics["inflow_rate"],
                outflow_rate=flow_metrics["outflow_rate"]
            )
            t_met1 = time.perf_counter()
            stage_timing["telemetry_generation_ms"] = round((t_met1 - t_met0) * 1000.0, 2)

            # Confidence score calculation
            base_confidence = 0.92 if self.is_calibrated else 0.75
            if not self.detector.model:
                base_confidence = 0.45
            if self.processing_mode == "LIVE" and not detections and not tracks:
                # Signal degraded feed state if no detections possible
                is_degraded = True
            else:
                is_degraded = not self.is_calibrated

            return {
                "timestamp": iso_timestamp,
                "camera_id": self.camera_id,
                "zone_id": self.zone_id,
                "density": density_val,
                "density_unit": density_unit,
                "density_confidence": round(base_confidence, 2),
                "inflow_rate": flow_metrics["inflow_rate"],
                "outflow_rate": flow_metrics["outflow_rate"],
                "flow_imbalance": flow_imbalance,
                "average_speed": speed_metrics["average_speed"],
                "median_speed": speed_metrics["median_speed"],
                "speed_unit": speed_metrics["speed_unit"],
                "stationary_ratio": speed_metrics["stationary_ratio"],
                "reverse_flow_ratio": direction_metrics["reverse_flow_ratio"],
                "direction_conflict_score": direction_metrics["direction_conflict_score"],
                "blockage_score": blockage,
                "person_count": person_count,
                "tracked_person_count": tracked_person_count,
                "tracks": tracks,
                "behavior_classification": behavior,
                "behavior_classifier_type": "RULE_BASED_BEHAVIOR_CLASSIFIER",
                "telemetry_source": "live_cctv_gps",
                "processing_mode": self.processing_mode,
                "calibration_status": calib_status,
                "confidence_score": round(base_confidence, 2),
                "is_degraded": is_degraded,
                "is_synthetic": (self.processing_mode == "SIMULATION"),
                "is_simulated": (self.processing_mode == "SIMULATION"),
                "stage_timing": stage_timing
            }

        else:  # "density_estimation" (CSRNet Dense Crowd Mode)
            dense_res = self.density_estimator.estimate_dense_crowd(raw_frame_or_telemetry, timestamp=now)
            density_val = dense_res["density_peds_m2"]
            self.last_density_estimate = density_val

            return {
                "timestamp": iso_timestamp,
                "camera_id": self.camera_id,
                "zone_id": self.zone_id,
                "density": density_val,
                "density_unit": "persons_per_m2" if self.is_calibrated else "NORMALIZED_ESTIMATE",
                "density_confidence": 0.65,
                "inflow_rate": 0.0,
                "outflow_rate": 0.0,
                "flow_imbalance": 0.0,
                "average_speed": 0.0,
                "median_speed": 0.0,
                "speed_unit": "m_s" if self.is_calibrated else "NORMALIZED_SPEED",
                "stationary_ratio": 1.0,
                "reverse_flow_ratio": 0.0,
                "direction_conflict_score": 0.50,
                "blockage_score": 0.85,
                "person_count": dense_res["estimated_headcount"],
                "tracked_person_count": 0,
                "tracks": [],
                "behavior_classification": "BOTTLENECK",
                "behavior_classifier_type": "RULE_BASED_BEHAVIOR_CLASSIFIER",
                "telemetry_source": "live_cctv_gps",
                "processing_mode": self.processing_mode,
                "calibration_status": "HOMOGRAPHY" if self.is_calibrated else "UNCALIBRATED",
                "confidence_score": 0.65,  # Reduced confidence due to absence of track velocity
                "is_degraded": False,
                "is_synthetic": (self.processing_mode == "SIMULATION"),
                "is_simulated": (self.processing_mode == "SIMULATION")
            }
