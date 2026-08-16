"""
CROWDSHIELD VIDEO REPLAY & TELEMETRY GENERATOR CLI
===================================================
Replays a local video file (MP4/AVI) through the real-time CV perception pipeline,
extracting frame-by-frame person detections, ByteTrack trajectories, and metric vectors.
Outputs deterministic JSON Lines (.jsonl) telemetry logs with complete data provenance.

Usage:
------
python backend/scripts/replay_video.py --video path/to/cctv.mp4 --zone-id zone-123 --output-jsonl telemetry_output.jsonl
"""

import sys
import os
import argparse
import json
import time
import logging

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.cv.camera_source import VideoFileSource
from app.ingestion.cv.pipeline import CVPipelineManager
from app.ingestion.cv.camera_health import CameraHealthTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("crowdshield.scripts.replay_video")


def run_video_replay(
    video_path: str,
    camera_id: str = "CAM-REPLAY-01",
    zone_id: str = "zone-demo-01",
    output_jsonl: Optional[str] = None,
    target_fps: int = 5,
    is_calibrated: bool = False,
    zone_area_m2: float = 200.0
) -> List[Dict[str, Any]]:
    """
    Executes deterministic video replay through CrowdShield perception pipeline.
    """
    logger.info(f"Starting video replay for file '{video_path}'...")
    source = VideoFileSource(camera_id=camera_id, video_path=video_path)

    if not source.is_open:
        logger.error(f"Cannot open video source: {video_path}")
        return []

    pipeline = CVPipelineManager(
        zone_id=zone_id,
        camera_id=camera_id,
        zone_area_m2=zone_area_m2,
        is_calibrated=is_calibrated,
        processing_mode="DEMO"
    )

    health_record = CameraHealthTracker.get_or_create(camera_id=camera_id, zone_id=zone_id)

    telemetry_records = []
    start_wall_time = time.time()
    frame_count = 0

    out_file = open(output_jsonl, "w") if output_jsonl else None

    try:
        while True:
            success, frame, metadata = source.read_frame()
            if not success or frame is None or metadata is None:
                break

            frame_count += 1
            health_record.record_frame(processed=True, detection_success=True)

            # Process frame through CVPipelineManager
            telemetry = pipeline.process_frame(
                raw_frame_or_telemetry=frame,
                timestamp=metadata.timestamp,
                frame_id=metadata.frame_id
            )

            # Strip non-serializable objects (e.g. tracks array internal deque) for JSONL
            record = {k: v for k, v in telemetry.items() if k != "tracks"}

            telemetry_records.append(record)

            if out_file:
                out_file.write(json.dumps(record) + "\n")

            if frame_count % 30 == 0:
                logger.info(
                    f"Replayed {frame_count} frames | Timestamp: {telemetry['timestamp']} | "
                    f"Persons: {telemetry['person_count']} | Density: {telemetry['density']} {telemetry['density_unit']} | "
                    f"Behavior: {telemetry['behavior_classification']}"
                )

    finally:
        source.release()
        if out_file:
            out_file.close()

    elapsed_wall_sec = max(0.001, time.time() - start_wall_time)
    avg_processing_fps = round(frame_count / elapsed_wall_sec, 2)

    logger.info(
        f"Completed video replay: {frame_count} frames processed in {round(elapsed_wall_sec, 2)}s "
        f"({avg_processing_fps} FPS processing speed)."
    )

    return telemetry_records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CrowdShield Video Replay Telemetry Generator")
    parser.add_argument("--video", type=str, required=True, help="Path to input video file")
    parser.add_argument("--camera-id", type=str, default="CAM-REPLAY-01", help="Camera ID")
    parser.add_argument("--zone-id", type=str, default="zone-demo-01", help="Zone ID")
    parser.add_argument("--output-jsonl", type=str, default=None, help="Output .jsonl path")
    parser.add_argument("--calibrated", action="store_true", help="Set zone calibration status to True")
    args = parser.parse_args()

    run_video_replay(
        video_path=args.video,
        camera_id=args.camera_id,
        zone_id=args.zone_id,
        output_jsonl=args.output_jsonl,
        is_calibrated=args.calibrated
    )
