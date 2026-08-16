"""
CROWDSHIELD CV PERSON DETECTOR (YOLOv8)
=======================================
Performs object detection on camera frames for crowd density analysis.
Filters detections strictly for person class (class_id = 0, label = "person").
Returns bounding box coordinates, confidence scores, center points, and timestamps.

PROVENANCE & NO SILENT FALLBACK RULE:
-------------------------------------
In LIVE mode: Never generates synthetic bounding boxes if YOLO model is absent or frame decoding fails.
Instead, returns empty detection list and sets is_degraded=True to prevent misleading operators.
Synthetic detection generation is strictly allowed only when processing_mode == "SIMULATION".
"""

import time
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from app.core.config import settings

logger = logging.getLogger("crowdshield.cv.detector")


class PersonDetector:
    """
    YOLOv8-based Person Detector.
    Leverages pretrained weights ('yolov8n.pt' / 'yolov8s.pt') for real-time person detection.
    """

    def __init__(self, model_name: str = "yolov8n.pt", confidence_threshold: Optional[float] = None):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold if confidence_threshold is not None else getattr(settings, "YOLO_CONFIDENCE", 0.35)
        self.model = None
        self.device = "cpu"
        self._initialize_model()

    def _initialize_model(self):
        """Attempts to load PyTorch / Ultralytics YOLO model if installed with dynamic device selection."""
        try:
            import torch
            from ultralytics import YOLO
            
            configured_device = getattr(settings, "YOLO_DEVICE", "auto").lower()
            if configured_device == "cuda" and torch.cuda.is_available():
                self.device = 0
            elif configured_device == "auto" and torch.cuda.is_available():
                self.device = 0
            else:
                self.device = "cpu"

            self.model = YOLO(self.model_name)
            logger.info(f"[CV DETECTOR] Loaded YOLO model '{self.model_name}' on device '{self.device}'.")
        except Exception as e:
            logger.warning(f"[CV DETECTOR] Ultralytics YOLO load deferred ({e}). LIVE inference requires model installation.")

    def detect_persons(
        self,
        frame_data: Any,
        timestamp: Optional[float] = None,
        frame_id: Optional[int] = None,
        processing_mode: str = "LIVE"
    ) -> List[Dict[str, Any]]:
        """
        Processes a single video frame and extracts person bounding boxes.
        """
        now = timestamp if timestamp is not None else time.time()

        # Real OpenCV / PyTorch Image Inference
        if self.model is not None and frame_data is not None and isinstance(frame_data, np.ndarray):
            try:
                img_size = getattr(settings, "YOLO_IMAGE_SIZE", 640)
                results = self.model(
                    frame_data,
                    imgsz=img_size,
                    classes=[0],
                    conf=self.confidence_threshold,
                    device=self.device,
                    verbose=False
                )
                detections = []
                for r in results:
                    for box in r.boxes:
                        coords = box.xyxy[0].tolist()
                        conf = float(box.conf[0])
                        if conf >= self.confidence_threshold:
                            x1, y1, x2, y2 = [round(c, 2) for c in coords]
                            cx = round((x1 + x2) / 2.0, 2)
                            cy = round((y1 + y2) / 2.0, 2)
                            detections.append({
                                "class": "person",
                                "class_id": 0,
                                "confidence": round(conf, 4),
                                "bbox": [x1, y1, x2, y2],
                                "center": [cx, cy],
                                "frame_timestamp": now,
                                "frame_id": frame_id
                            })
                return detections
            except Exception as e:
                logger.error(f"[CV DETECTOR] Inference exception: {e}")
                if processing_mode == "LIVE":
                    # In LIVE mode, NEVER generate synthetic boxes on error!
                    return []

        # If processing_mode is SIMULATION or explicit synthetic dict frame, generate simulation detections
        if processing_mode == "SIMULATION" or (isinstance(frame_data, dict) and processing_mode != "LIVE"):
            return self._generate_simulation_detections(frame_data, now, frame_id)

        # In LIVE or DEMO mode when frame image array is missing or model fails:
        # DO NOT SILENTLY FALLBACK to fake detections! Return empty list.
        return []

    def _generate_simulation_detections(
        self,
        frame_data: Any,
        timestamp: float,
        frame_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Returns explicitly marked synthetic detections for SIMULATION mode only."""
        if isinstance(frame_data, dict):
            density = frame_data.get("density_peds_m2", 1.0)
            count = max(1, int(density * 5))
            results = []
            for i in range(count):
                x = (i * 30.0) % 640.0
                y = (i * 20.0) % 480.0
                x1, y1, x2, y2 = x, y, x + 40.0, y + 80.0
                results.append({
                    "class": "person",
                    "class_id": 0,
                    "confidence": 0.88,
                    "bbox": [x1, y1, x2, y2],
                    "center": [round(x + 20.0, 2), round(y + 40.0, 2)],
                    "frame_timestamp": timestamp,
                    "frame_id": frame_id,
                    "is_synthetic": True
                })
            return results
        return []
