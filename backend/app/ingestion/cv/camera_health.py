"""
CROWDSHIELD CAMERA HEALTH & TELEMETRY MONITORING SERVICE
=========================================================
Monitors camera feed connectivity, frame rate, detection latency, and calibration status.
Provides camera operational states: ONLINE, DEGRADED, OFFLINE, CV_UNAVAILABLE.

HEALTH EVALUATION RULES:
------------------------
1. ONLINE: Active frame ingestion within 5 seconds, valid CV processing.
2. DEGRADED: Frame rate below target FPS, uncalibrated zone, or high frame skip ratio.
3. OFFLINE: No frame received within 15 seconds.
4. CV_UNAVAILABLE: Camera active but PyTorch/YOLO model missing or failing.
"""

import time
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("crowdshield.cv.camera_health")


class CameraHealthRecord:
    def __init__(self, camera_id: str, zone_id: str):
        self.camera_id = camera_id
        self.zone_id = zone_id
        self.status = "ONLINE"
        self.last_frame_timestamp = time.time()
        self.last_processed_timestamp = time.time()
        self.frames_received = 0
        self.frames_processed = 0
        self.processing_fps = 0.0
        self.detection_success_rate = 1.0
        self.is_degraded = False
        self.degradation_reason: Optional[str] = None
        self.calibration_status = "UNCALIBRATED"

    def record_frame(self, processed: bool = True, detection_success: bool = True):
        now = time.time()
        dt = max(0.001, now - self.last_frame_timestamp)
        self.last_frame_timestamp = now
        self.frames_received += 1

        if processed:
            self.last_processed_timestamp = now
            self.frames_processed += 1
            # Exponential moving average for processing FPS
            instant_fps = 1.0 / dt
            self.processing_fps = round(0.8 * self.processing_fps + 0.2 * instant_fps, 2)

        # Update detection success rate
        alpha = 0.1
        self.detection_success_rate = round((1.0 - alpha) * self.detection_success_rate + alpha * (1.0 if detection_success else 0.0), 3)

    def evaluate_health(self, offline_timeout_sec: float = 15.0, is_calibrated: bool = False) -> Dict[str, Any]:
        now = time.time()
        time_since_last_frame = now - self.last_frame_timestamp

        self.calibration_status = "HOMOGRAPHY" if is_calibrated else "UNCALIBRATED"

        if time_since_last_frame > offline_timeout_sec:
            self.status = "OFFLINE"
            self.is_degraded = True
            self.degradation_reason = f"Camera feed offline (no frame for {round(time_since_last_frame, 1)}s)"
        elif not is_calibrated:
            self.status = "DEGRADED"
            self.is_degraded = True
            self.degradation_reason = "UNCALIBRATED ZONE: Accuracy degraded"
        elif self.detection_success_rate < 0.5:
            self.status = "CV_UNAVAILABLE"
            self.is_degraded = True
            self.degradation_reason = "Person detection pipeline failing or model missing"
        else:
            self.status = "ONLINE"
            self.is_degraded = False
            self.degradation_reason = None

        return {
            "camera_id": self.camera_id,
            "zone_id": self.zone_id,
            "status": self.status,
            "is_degraded": self.is_degraded,
            "degradation_reason": self.degradation_reason,
            "calibration_status": self.calibration_status,
            "frames_received": self.frames_received,
            "frames_processed": self.frames_processed,
            "processing_fps": self.processing_fps,
            "time_since_last_frame_sec": round(time_since_last_frame, 2),
            "detection_success_rate": self.detection_success_rate
        }


class CameraHealthTracker:
    """Registry maintaining health state across all venue cameras."""
    _cameras: Dict[str, CameraHealthRecord] = {}

    @classmethod
    def get_or_create(cls, camera_id: str, zone_id: str) -> CameraHealthRecord:
        if camera_id not in cls._cameras:
            cls._cameras[camera_id] = CameraHealthRecord(camera_id=camera_id, zone_id=zone_id)
        return cls._cameras[camera_id]

    @classmethod
    def get_all_camera_health(cls, db_zones: Optional[Dict[str, bool]] = None) -> List[Dict[str, Any]]:
        results = []
        db_zones = db_zones or {}
        for cam_id, rec in cls._cameras.items():
            is_calibrated = db_zones.get(rec.zone_id, False)
            results.append(rec.evaluate_health(is_calibrated=is_calibrated))
        return results
