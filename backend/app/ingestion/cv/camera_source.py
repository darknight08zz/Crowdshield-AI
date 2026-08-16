"""
CROWDSHIELD CAMERA SOURCE ABSTRACTION & FRAME INGESTION MODULE
==============================================================
Provides clean abstraction for camera frame ingestion across diverse video inputs:
1. Video File (MP4, AVI, MKV) - Video-relative reproducible timestamps
2. Webcam (local USB / integrated camera device indices)
3. RTSP Stream (network CCTV streams)

Tracks frame metadata:
- camera_id: Unique identifier
- frame_id: Monotonic integer frame index
- timestamp: Relative video timestamp (seconds) or wall-clock epoch timestamp
- fps: Native or target FPS
- width, height: Frame resolution
- source_type: "VIDEO_FILE" | "WEBCAM" | "RTSP" | "SYNTHETIC"
"""

import time
import logging
import threading
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any, Optional
import numpy as np

logger = logging.getLogger("crowdshield.cv.camera_source")


class FrameMetadata:
    def __init__(
        self,
        camera_id: str,
        frame_id: int,
        timestamp: float,
        fps: float,
        width: int,
        height: int,
        source_type: str
    ):
        self.camera_id = camera_id
        self.frame_id = frame_id
        self.timestamp = timestamp
        self.fps = fps
        self.width = width
        self.height = height
        self.source_type = source_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "frame_id": self.frame_id,
            "timestamp": round(self.timestamp, 4),
            "fps": round(self.fps, 2),
            "width": self.width,
            "height": self.height,
            "source_type": self.source_type
        }


class CameraSource(ABC):
    """Abstract base class for all camera input sources."""

    def __init__(self, camera_id: str, source_type: str):
        self.camera_id = camera_id
        self.source_type = source_type
        self.frame_counter = 0
        self.is_open = False

    @abstractmethod
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], Optional[FrameMetadata]]:
        """
        Reads the next video frame.

        Returns:
            Tuple[bool, Optional[np.ndarray], Optional[FrameMetadata]]:
            (success, frame_bgr_array, frame_metadata)
        """
        pass

    @abstractmethod
    def release(self):
        """Releases underlying video capture resources."""
        pass


class VideoFileSource(CameraSource):
    """
    Ingests frames from a local video file (MP4, AVI, etc.).
    Uses video-relative timestamps for deterministic replay testing.
    """

    def __init__(self, camera_id: str, video_path: str):
        super().__init__(camera_id=camera_id, source_type="VIDEO_FILE")
        self.video_path = video_path
        self.cap = None
        self.fps = 30.0
        self.width = 1280
        self.height = 720
        self.total_frames = 0
        self._open()

    def _open(self):
        try:
            import cv2
            self.cap = cv2.VideoCapture(self.video_path)
            if self.cap.isOpened():
                self.is_open = True
                self.fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 30.0)
                self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
                self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                logger.info(f"[CAMERA SOURCE] Opened VideoFileSource '{self.camera_id}' ({self.video_path}): {self.width}x{self.height} @ {self.fps} FPS, total {self.total_frames} frames.")
            else:
                logger.error(f"[CAMERA SOURCE] Failed to open video file '{self.video_path}'.")
                self.is_open = False
        except Exception as e:
            logger.error(f"[CAMERA SOURCE] Exception opening VideoFileSource: {e}")
            self.is_open = False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], Optional[FrameMetadata]]:
        if not self.is_open or self.cap is None:
            return False, None, None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return False, None, None

        self.frame_counter += 1
        # Reproducible video-relative timestamp in seconds
        rel_timestamp = (self.frame_counter - 1) / max(1.0, self.fps)

        metadata = FrameMetadata(
            camera_id=self.camera_id,
            frame_id=self.frame_counter,
            timestamp=rel_timestamp,
            fps=self.fps,
            width=frame.shape[1],
            height=frame.shape[0],
            source_type=self.source_type
        )
        return True, frame, metadata

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.is_open = False


class WebcamSource(CameraSource):
    """
    Ingests frames from a local USB/integrated webcam device.
    """

    def __init__(self, camera_id: str, device_index: int = 0):
        super().__init__(camera_id=camera_id, source_type="WEBCAM")
        self.device_index = device_index
        self.cap = None
        self.fps = 30.0
        self.width = 640
        self.height = 480
        self._open()

    def _open(self):
        try:
            import cv2
            self.cap = cv2.VideoCapture(self.device_index)
            if self.cap.isOpened():
                self.is_open = True
                self.fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 30.0)
                self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
                self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
                logger.info(f"[CAMERA SOURCE] Opened WebcamSource '{self.camera_id}' (device {self.device_index}).")
            else:
                self.is_open = False
        except Exception as e:
            logger.error(f"[CAMERA SOURCE] Exception opening WebcamSource: {e}")
            self.is_open = False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], Optional[FrameMetadata]]:
        if not self.is_open or self.cap is None:
            return False, None, None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return False, None, None

        self.frame_counter += 1
        now = time.time()
        metadata = FrameMetadata(
            camera_id=self.camera_id,
            frame_id=self.frame_counter,
            timestamp=now,
            fps=self.fps,
            width=frame.shape[1],
            height=frame.shape[0],
            source_type=self.source_type
        )
        return True, frame, metadata

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.is_open = False


class RTSPSource(CameraSource):
    """
    Ingests frames from an RTSP network CCTV stream.
    """

    def __init__(self, camera_id: str, rtsp_url: str):
        super().__init__(camera_id=camera_id, source_type="RTSP")
        self.rtsp_url = rtsp_url
        self.cap = None
        self.fps = 25.0
        self.width = 1920
        self.height = 1080
        self._open()

    def _open(self):
        try:
            import cv2
            self.cap = cv2.VideoCapture(self.rtsp_url)
            if self.cap.isOpened():
                self.is_open = True
                self.fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 25.0)
                self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
                self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)
                logger.info(f"[CAMERA SOURCE] Opened RTSPSource '{self.camera_id}'.")
            else:
                self.is_open = False
        except Exception as e:
            logger.error(f"[CAMERA SOURCE] Exception opening RTSPSource: {e}")
            self.is_open = False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], Optional[FrameMetadata]]:
        if not self.is_open or self.cap is None:
            return False, None, None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return False, None, None

        self.frame_counter += 1
        now = time.time()
        metadata = FrameMetadata(
            camera_id=self.camera_id,
            frame_id=self.frame_counter,
            timestamp=now,
            fps=self.fps,
            width=frame.shape[1],
            height=frame.shape[0],
            source_type=self.source_type
        )
        return True, frame, metadata

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.is_open = False


class LatestFrameBuffer:
    """
    Thread-safe single-slot frame buffer for managing frame ingestion backpressure.
    Decouples camera frame capture rate from CV inference processing rate.
    When CV inference is slower than camera frame rate, old unread frames are dropped
    so the inference worker always receives the newest available frame.
    """

    def __init__(self, maxsize: int = 1):
        self.maxsize = maxsize
        self._lock = threading.Lock()
        self._latest_item: Optional[Tuple[np.ndarray, FrameMetadata]] = None
        
        # Diagnostic Counters
        self.frames_received = 0
        self.frames_processed = 0
        self.frames_dropped = 0
        
        self.start_time = time.time()
        self.last_process_time = time.time()

    def push(self, frame: np.ndarray, metadata: FrameMetadata) -> int:
        """
        Pushes a new frame into the buffer.
        If an unread frame was already present, it is replaced and frames_dropped is incremented.
        """
        with self._lock:
            self.frames_received += 1
            if self._latest_item is not None:
                self.frames_dropped += 1
            self._latest_item = (frame, metadata)
            return self.frames_dropped

    def get_latest(self) -> Tuple[bool, Optional[np.ndarray], Optional[FrameMetadata]]:
        """
        Retrieves the newest available frame from the buffer.
        """
        with self._lock:
            if self._latest_item is None:
                return False, None, None
            
            frame, metadata = self._latest_item
            self._latest_item = None
            self.frames_processed += 1
            self.last_process_time = time.time()
            return True, frame, metadata

    def get_diagnostics(self) -> Dict[str, Any]:
        """Returns frame backpressure diagnostic metrics."""
        with self._lock:
            elapsed = max(0.001, time.time() - self.start_time)
            source_fps = self.frames_received / elapsed
            processing_fps = self.frames_processed / elapsed
            return {
                "frames_received": self.frames_received,
                "frames_processed": self.frames_processed,
                "frames_dropped": self.frames_dropped,
                "source_fps": round(source_fps, 2),
                "processing_fps": round(processing_fps, 2),
                "buffer_has_unread": self._latest_item is not None
            }

