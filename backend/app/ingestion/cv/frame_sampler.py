"""
CROWDSHIELD CV FRAME SAMPLER
============================
Filters native camera RTSP streams (typically ~30 FPS) down to a configurable sample rate (FRAME_SAMPLE_RATE).

PERFORMANCE & COMPUTE TRADEOFF EXPLANATION:
------------------------------------------
1. Higher Sample Rate (10-15 FPS):
   - Advantages: Smoother bounding box tracking trajectories, lower latency detection of sudden direction flips or surges.
   - Disadvantages: Proportionally higher GPU/CPU inference cost (2x - 3x FLOPS). Can saturate edge devices if monitoring 16+ streams.

2. Lower Sample Rate (3-5 FPS):
   - Advantages: Highly efficient CPU/GPU utilization, enables scaling to dozens of concurrent RTSP camera feeds per edge node.
   - Disadvantages: Higher velocity variance across sampled frames; tracking association requires wider Kalman search windows.

By exposing FRAME_SAMPLE_RATE via settings/environment configuration, event engineers can tune
compute budget dynamically per venue without code modifications.
"""

import time
from typing import Optional
from app.core.config import settings


class FrameSampler:
    """
    Stateful frame sampler per RTSP camera stream.
    Determines whether the incoming frame at current_time should be processed or skipped.
    """

    def __init__(self, target_fps: Optional[int] = None, native_fps: int = 30):
        self.target_fps = target_fps if target_fps is not None else settings.FRAME_SAMPLE_RATE
        self.native_fps = native_fps
        self.sample_interval_sec = 1.0 / float(max(1, self.target_fps))
        self.last_processed_timestamp = 0.0
        self.total_frames_received = 0
        self.total_frames_processed = 0

    def should_process_frame(self, current_time: Optional[float] = None) -> bool:
        """
        Returns True if the current frame satisfies the target FPS sample interval.
        """
        now = current_time if current_time is not None else time.time()
        self.total_frames_received += 1

        if (now - self.last_processed_timestamp) >= self.sample_interval_sec:
            self.last_processed_timestamp = now
            self.total_frames_processed += 1
            return True
        return False

    def get_stats(self) -> dict:
        """Returns sampling efficiency statistics."""
        skip_ratio = 1.0 - (self.total_frames_processed / max(1, self.total_frames_received))
        return {
            "target_fps": self.target_fps,
            "total_received": self.total_frames_received,
            "total_processed": self.total_frames_processed,
            "skip_ratio": round(skip_ratio, 4)
        }
