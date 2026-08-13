"""
TEST SUITE FOR COMPUTER VISION DETECTION PIPELINE (Addendum Prompt 1)
====================================================================
Verifies frame sampling, YOLOv8 detection formatting, ByteTrack tracking,
CSRNet dense-crowd fallback, dynamic strategy selection, and confidence degradation.
"""

import pytest
import time
from app.ingestion.cv.frame_sampler import FrameSampler
from app.ingestion.cv.detector import PersonDetector
from app.ingestion.cv.tracker import ByteTracker
from app.ingestion.cv.density_estimator import DensityEstimator
from app.ingestion.cv.strategy import select_detection_strategy, StrategySwitchLogger
from app.ingestion.cv.pipeline import CVPipelineManager


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


def test_person_detector_output_contract():
    """Verifies PersonDetector outputs bbox, confidence, class_id=0, and timestamp."""
    detector = PersonDetector(confidence_threshold=0.35)
    detections = detector.detect_persons({"density_peds_m2": 1.2}, timestamp=time.time())

    assert len(detections) > 0
    det = detections[0]
    assert "bbox" in det and len(det["bbox"]) == 4
    assert "confidence" in det and det["confidence"] >= 0.35
    assert det["class_id"] == 0
    assert "frame_timestamp" in det


def test_bytetrack_persistent_ids_and_velocity():
    """Verifies ByteTracker assigns persistent track_ids and calculates velocity vectors."""
    tracker = ByteTracker(iou_threshold=0.30)
    t0 = time.time()

    dets_frame1 = [{"bbox": [100.0, 100.0, 150.0, 200.0], "confidence": 0.90, "class_id": 0}]
    tracks_f1 = tracker.update(dets_frame1, timestamp=t0)
    assert len(tracks_f1) == 1
    track_id = tracks_f1[0]["track_id"]

    # Frame 2 (0.1s later, shifted bbox)
    t1 = t0 + 0.1
    dets_frame2 = [{"bbox": [110.0, 100.0, 160.0, 200.0], "confidence": 0.92, "class_id": 0}]
    tracks_f2 = tracker.update(dets_frame2, timestamp=t1)

    assert len(tracks_f2) == 1
    assert tracks_f2[0]["track_id"] == track_id  # Persistent track ID maintained
    assert tracks_f2[0]["velocity"][0] > 0.0      # Positive X velocity calculated


def test_csrnet_dense_crowd_estimator():
    """Verifies CSRNet headcount integration when occlusion threshold is exceeded."""
    estimator = DensityEstimator(zone_area_m2=100.0)
    res = estimator.estimate_dense_crowd({"density_peds_m2": 3.80})

    assert res["estimated_headcount"] == 380
    assert res["density_peds_m2"] == 3.80
    assert res["has_individual_tracks"] is False


def test_dynamic_strategy_selector_with_hysteresis():
    """Verifies per-zone dynamic strategy switching and hysteresis buffer logging."""
    zone_id = "test-zone-999"

    # Moderate density -> detection_tracking
    strat, _ = select_detection_strategy(zone_id, recent_density_estimate=1.2)
    assert strat == "detection_tracking"

    # 3 consecutive high-density readings trigger switch to density_estimation
    select_detection_strategy(zone_id, 3.2)
    select_detection_strategy(zone_id, 3.4)
    strat, reason = select_detection_strategy(zone_id, 3.5)

    assert strat == "density_estimation"
    assert "High occlusion" in reason

    # Check switch audit log
    latest_log = StrategySwitchLogger.history[-1]
    assert latest_log["zone_id"] == zone_id
    assert latest_log["new_strategy"] == "density_estimation"


def test_cv_pipeline_manager_output_contract():
    """Verifies CVPipelineManager exposes standard contract and graceful confidence degradation."""
    mgr = CVPipelineManager(zone_id="test-zone-100", zone_area_m2=200.0)

    # 1. Moderate density test (detection_tracking mode)
    out1 = mgr.process_frame({"density_peds_m2": 1.2})
    assert out1["strategy"] == "detection_tracking"
    assert out1["confidence_score"] >= 0.90
    assert len(out1["tracks"]) > 0

    # 2. Dense crowd test (density_estimation mode)
    out2 = mgr.process_frame({"density_peds_m2": 3.8})
    # Force 3 steps to trigger hysteresis switch
    mgr.process_frame({"density_peds_m2": 3.8})
    out2 = mgr.process_frame({"density_peds_m2": 3.8})

    assert out2["strategy"] == "density_estimation"
    assert out2["confidence_score"] == 0.65  # Degraded confidence due to lack of track velocity
    assert len(out2["tracks"]) == 0
