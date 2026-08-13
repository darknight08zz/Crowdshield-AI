"""
CROWDSHIELD COMPUTER VISION INGESTION PIPELINE
===============================================
Provides person detection (YOLOv8), multi-object tracking (ByteTrack),
dense-crowd fallback (CSRNet density maps), and dynamic strategy selection per zone.
"""

from app.ingestion.cv.frame_sampler import FrameSampler
from app.ingestion.cv.detector import PersonDetector
from app.ingestion.cv.tracker import ByteTracker
from app.ingestion.cv.density_estimator import DensityEstimator
from app.ingestion.cv.strategy import select_detection_strategy, StrategySwitchLogger
from app.ingestion.cv.pipeline import CVPipelineManager

__all__ = [
    "FrameSampler",
    "PersonDetector",
    "ByteTracker",
    "DensityEstimator",
    "select_detection_strategy",
    "StrategySwitchLogger",
    "CVPipelineManager",
]
