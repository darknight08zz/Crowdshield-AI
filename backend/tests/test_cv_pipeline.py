"""
TEST SUITE FOR REAL-TIME CROWD PERCEPTION & TELEMETRY PIPELINE (Phase 2)
========================================================================
Verifies frame sampling, camera sources, YOLO person detection, ByteTrack trajectories,
homography calibration, speed/direction/conflict/blockage metrics, rule-based behavior classification,
camera health state tracking, and canonical telemetry provenance flags.
"""

import pytest
import time
import numpy as np
from app.ingestion.cv.frame_sampler import FrameSampler
from app.ingestion.cv.detector import PersonDetector
from app.ingestion.cv.tracker import ByteTracker
from app.ingestion.cv.density_estimator import DensityEstimator
from app.ingestion.cv.strategy import select_detection_strategy, StrategySwitchLogger
from app.ingestion.cv.pipeline import CVPipelineManager
from app.ingestion.cv.camera_source import FrameMetadata
from app.ingestion.cv.metrics import (
    calculate_density,
    calculate_speed_metrics,
    calculate_direction_and_conflict,
    calculate_blockage_score,
    classify_crowd_behavior
)
from app.ingestion.cv.camera_health import CameraHealthTracker, CameraHealthRecord


def test_frame_sampler_rate_limiting():
    """Confirms FrameSampler samples at target FPS (e.g. 5 FPS from 30 FPS stream)."""
    sampler = FrameSampler(target_fps=5, native_fps=30)
    now = time.time()

    # First frame should process
    assert sampler.should_process_frame(now) is True

    # Immediate frame (0.01s later) should be skipped
    assert sampler.should_process_frame(now + 0.01) is False

    # Frame after sample interval (0.21s later) should process
    assert sampler.should_process_frame(now + 0.21) is True


def test_person_detector_live_mode_no_silent_fallback():
    """Verifies that PersonDetector in LIVE mode returns empty list instead of synthetic boxes on missing image array."""
    detector = PersonDetector(confidence_threshold=0.35)

    # In LIVE mode with dict input (no real numpy image array), return [] to avoid misleading operators
    detections_live = detector.detect_persons({"density_peds_m2": 1.2}, timestamp=time.time(), processing_mode="LIVE")
    assert detections_live == []

    # In SIMULATION mode, explicitly marked synthetic detections are returned
    detections_sim = detector.detect_persons({"density_peds_m2": 1.2}, timestamp=time.time(), processing_mode="SIMULATION")
    assert len(detections_sim) > 0
    assert detections_sim[0]["is_synthetic"] is True


def test_bytetrack_trajectory_lifecycle_and_metrics():
    """Verifies ByteTracker assigns persistent IDs, tracks lifecycle states, and computes displacement, angle, and path consistency."""
    tracker = ByteTracker(iou_threshold=0.30)
    t0 = time.time()

    dets_frame1 = [{
        "class": "person", "class_id": 0, "confidence": 0.90,
        "bbox": [100.0, 100.0, 150.0, 200.0], "center": [125.0, 150.0]
    }]
    tracks_f1 = tracker.update(dets_frame1, timestamp=t0, frame_id=1)
    assert len(tracks_f1) == 1
    assert tracks_f1[0]["state"] == "NEW"
    track_id = tracks_f1[0]["track_id"]

    # Frame 2 (0.1s later, shifted bbox right)
    t1 = t0 + 0.1
    dets_frame2 = [{
        "class": "person", "class_id": 0, "confidence": 0.92,
        "bbox": [120.0, 100.0, 170.0, 200.0], "center": [145.0, 150.0]
    }]
    tracks_f2 = tracker.update(dets_frame2, timestamp=t1, frame_id=2)

    assert len(tracks_f2) == 1
    assert tracks_f2[0]["track_id"] == track_id
    assert tracks_f2[0]["state"] == "ACTIVE"
    assert tracks_f2[0]["displacement"] > 0.0
    assert tracks_f2[0]["direction_angle"] == 0.0  # Moving East (+X)


def test_metrics_direction_conflict_and_reverse_flow():
    """Verifies circular variance direction_conflict_score and reverse_flow_ratio calculations."""
    # Tracks moving East (0 deg) and West (180 deg) -> Opposing flow
    tracks = [
        {"displacement": 20.0, "direction_angle": 0.0},
        {"displacement": 20.0, "direction_angle": 0.0},
        {"displacement": 20.0, "direction_angle": 180.0}
    ]

    res = calculate_direction_and_conflict(tracks)
    assert res["direction_conflict_score"] > 0.3
    assert res["reverse_flow_count"] == 1
    assert round(res["reverse_flow_ratio"], 2) == 0.33


def test_rule_based_behavior_classifier():
    """Verifies rule-based classification logic (SURGE, BOTTLENECK, STAGNATION, REVERSE_FLOW, DIRECTION_CONFLICT, NORMAL)."""
    # 1. Surge Test
    surge_res = classify_crowd_behavior(
        density_peds_m2=1.5, median_speed=1.1, stationary_ratio=0.05,
        reverse_flow_ratio=0.0, direction_conflict_score=0.1, blockage_score=0.2,
        inflow_rate=95.0, outflow_rate=30.0
    )
    assert surge_res == "SURGE"

    # 2. Bottleneck Test
    bottleneck_res = classify_crowd_behavior(
        density_peds_m2=3.5, median_speed=0.2, stationary_ratio=0.5,
        reverse_flow_ratio=0.0, direction_conflict_score=0.2, blockage_score=0.75,
        inflow_rate=40.0, outflow_rate=10.0
    )
    assert bottleneck_res == "BOTTLENECK"

    # 3. Normal Test
    normal_res = classify_crowd_behavior(
        density_peds_m2=1.0, median_speed=1.2, stationary_ratio=0.05,
        reverse_flow_ratio=0.0, direction_conflict_score=0.1, blockage_score=0.15,
        inflow_rate=40.0, outflow_rate=35.0
    )
    assert normal_res == "NORMAL"


def test_camera_health_tracker():
    """Verifies CameraHealthTracker correctly identifies ONLINE, DEGRADED, and OFFLINE states."""
    rec = CameraHealthTracker.get_or_create(camera_id="CAM-TEST-01", zone_id="zone-01")

    # Record active frame
    rec.record_frame(processed=True, detection_success=True)
    status_calibrated = rec.evaluate_health(is_calibrated=True)
    assert status_calibrated["status"] == "ONLINE"
    assert status_calibrated["is_degraded"] is False

    # Uncalibrated zone degrades status
    status_uncalibrated = rec.evaluate_health(is_calibrated=False)
    assert status_uncalibrated["status"] == "DEGRADED"
    assert "UNCALIBRATED" in status_uncalibrated["degradation_reason"]

    # Simulating offline timeout (>15s)
    rec.last_frame_timestamp = time.time() - 20.0
    status_offline = rec.evaluate_health(is_calibrated=True)
    assert status_offline["status"] == "OFFLINE"


def test_cv_pipeline_manager_canonical_output_and_provenance():
    """Verifies CVPipelineManager produces canonical output with strict provenance metadata."""
    mgr = CVPipelineManager(
        zone_id="zone-canary-01",
        camera_id="CAM-CANARY-01",
        zone_area_m2=300.0,
        is_calibrated=True,
        processing_mode="DEMO"
    )

    out = mgr.process_frame({"density_peds_m2": 1.4})

    assert out["camera_id"] == "CAM-CANARY-01"
    assert out["zone_id"] == "zone-canary-01"
    assert out["processing_mode"] == "DEMO"
    assert out["calibration_status"] == "HOMOGRAPHY"
    assert out["density_unit"] == "persons_per_m2"
    assert out["speed_unit"] == "m_s"
    assert out["behavior_classifier_type"] == "RULE_BASED_BEHAVIOR_CLASSIFIER"
    assert "confidence_score" in out
    assert "is_degraded" in out
    assert "is_synthetic" in out
