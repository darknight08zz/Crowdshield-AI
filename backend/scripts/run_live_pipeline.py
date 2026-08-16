"""
CROWDSHIELD — PHASE 6E LIVE PIPELINE RUNNER
===========================================
Executes full real-time computer vision and AI forecasting pipeline from live input sources:
- VIDEO_FILE (MP4/AVI/MKV)
- WEBCAM (Local USB/Integrated device)
- RTSP (Network CCTV camera stream)

Data Flow:
CameraSource -> CVPipelineManager (YOLOv8 + ByteTrack) -> Telemetry -> RealtimeInferenceOrchestrator -> 
ResultStore -> RealtimeStreamManager (WebSocket) -> Incident Policy Engine -> Field Officer Dispatch

Usage Examples:
---------------
1. Video file mode:
   python backend/scripts/run_live_pipeline.py --source video --video path/to/crowd.mp4 --realtime

2. Webcam mode:
   python backend/scripts/run_live_pipeline.py --source webcam --camera-index 0

3. RTSP stream mode:
   python backend/scripts/run_live_pipeline.py --source rtsp --url rtsp://admin:pass@192.168.1.100:554/stream1
"""

import os
import sys
import time
import json
import logging
import argparse
from typing import Optional, Dict, Any, Tuple
import numpy as np

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.cv.camera_source import (
    CameraSource,
    VideoFileSource,
    WebcamSource,
    RTSPSource,
    FrameMetadata
)
from app.ingestion.cv.pipeline import CVPipelineManager
from app.ingestion.cv.camera_health import CameraHealthTracker
from app.ai.services.inference_orchestrator import RealtimeInferenceOrchestrator
from app.ai.services.realtime_result_store import RealtimeInferenceResultStore
from app.services.realtime_stream import realtime_stream_manager
from app.services.incident_service import evaluate_incident_policy, process_realtime_inference_incident

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("crowdshield.scripts.run_live_pipeline")


def generate_sample_crowd_video(output_path: str, duration_sec: int = 10, fps: int = 30) -> str:
    """
    Creates a sample crowd video file using OpenCV if no external video is provided.
    Leverages realistic CCTV photographic crowd asset if available to ensure YOLOv8 detects real persons.
    """
    import cv2
    logger.info(f"[LIVE PIPELINE] Generating sample crowd video at '{output_path}' ({duration_sec}s @ {fps} FPS)...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    base_img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "cctv_crowd_base.png"))
    base_img = cv2.imread(base_img_path) if os.path.exists(base_img_path) else None

    target_w, target_h = 1280, 720
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (target_w, target_h))

    total_frames = duration_sec * fps
    for f in range(total_frames):
        if base_img is not None:
            bh, bw, _ = base_img.shape
            # Smooth pan across base photographic crowd image
            dx = int(f * 3.5) % max(1, bw - target_w)
            dy = int(f * 2.0) % max(1, bh - target_h)
            
            # Crop 1280x720 window
            crop = base_img[dy:dy+target_h, dx:dx+target_w]
            if crop.shape[0] < target_h or crop.shape[1] < target_w:
                frame = cv2.resize(base_img, (target_w, target_h))
            else:
                frame = crop.copy()
        else:
            frame = np.full((target_h, target_w, 3), (30, 30, 35), dtype=np.uint8)
            num_persons = min(50, 10 + (f // 6))
            for i in range(num_persons):
                cx = int((i * 45 + f * 3) % (target_w - 100) + 50)
                cy = int((i * 35 + np.sin(f * 0.1 + i) * 20) % (target_h - 100) + 50)
                cv2.circle(frame, (cx, cy), 14, (220, 200, 80), -1)
                cv2.rectangle(frame, (cx - 16, cy + 14), (cx + 16, cy + 55), (190, 130, 50), -1)

        cv2.putText(frame, f"CrowdShield Live Feed Frame {f+1}/{total_frames}", (30, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        out.write(frame)

    out.release()
    logger.info(f"[LIVE PIPELINE] Successfully generated sample crowd video: '{output_path}'")
    return output_path


def build_camera_source(
    source_type: str,
    video_path: Optional[str],
    camera_index: int,
    rtsp_url: Optional[str],
    camera_id: str
) -> CameraSource:
    """Instantiates the appropriate CameraSource subclass based on input mode."""
    if source_type == "video":
        target_path = video_path
        if not target_path or not os.path.exists(target_path):
            sample_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "sample_crowd.mp4"))
            if not os.path.exists(sample_file):
                generate_sample_crowd_video(sample_file)
            target_path = sample_file
            logger.info(f"[LIVE PIPELINE] Using sample video file: '{target_path}'")
        return VideoFileSource(camera_id=camera_id, video_path=target_path)

    elif source_type == "webcam":
        logger.info(f"[LIVE PIPELINE] Connecting to local webcam device index {camera_index}...")
        return WebcamSource(camera_id=camera_id, device_index=camera_index)

    elif source_type == "rtsp":
        if not rtsp_url:
            raise ValueError("[LIVE PIPELINE] RTSP URL '--url' must be provided for 'rtsp' source mode.")
        logger.info(f"[LIVE PIPELINE] Connecting to RTSP stream: '{rtsp_url}'...")
        return RTSPSource(camera_id=camera_id, rtsp_url=rtsp_url)

    else:
        raise ValueError(f"[LIVE PIPELINE] Unsupported source type '{source_type}'. Choose 'video', 'webcam', or 'rtsp'.")


def run_live_pipeline(
    source_type: str = "video",
    video_path: Optional[str] = None,
    camera_index: int = 0,
    rtsp_url: Optional[str] = None,
    event_id: str = "EVT-LIVE-01",
    camera_id: str = "CAM-LIVE-01",
    zone_id: str = "22222222-2222-2222-2222-222222222222",
    realtime: bool = False,
    max_frames: int = 0,
    broadcast: bool = False
) -> Dict[str, Any]:
    """
    Executes the Phase 6E live pipeline loop.
    """
    logger.info("==========================================================")
    logger.info("CROWDSHIELD PHASE 6E — LIVE PIPELINE INITIALIZATION")
    logger.info("==========================================================")
    logger.info(f"Mode: {source_type.upper()} | Event: {event_id} | Camera: {camera_id} | Zone: {zone_id}")

    # Initialize Camera Source
    cam_source = build_camera_source(source_type, video_path, camera_index, rtsp_url, camera_id)
    if not cam_source.is_open:
        logger.error(f"[LIVE PIPELINE] Failed to initialize camera source for mode '{source_type}'.")
        return {"status": "FAILED", "error": "Camera source could not be opened."}

    # Initialize RealtimeInferenceOrchestrator & ResultStore
    orchestrator = RealtimeInferenceOrchestrator()
    result_store = RealtimeInferenceResultStore()

    # Initialize Camera Health Tracker
    health_tracker = CameraHealthTracker.get_or_create(camera_id=camera_id, zone_id=zone_id)

    processed_frames = 0
    start_time = time.time()
    latencies = []

    try:
        while True:
            if max_frames > 0 and processed_frames >= max_frames:
                logger.info(f"[LIVE PIPELINE] Reached max frames limit ({max_frames}). Stopping pipeline loop.")
                break

            t0 = time.time()
            success, frame, metadata = cam_source.read_frame()

            if not success or frame is None or metadata is None:
                if cam_source.source_type == "VIDEO_FILE":
                    logger.info("[LIVE PIPELINE] Video file playback completed.")
                    break
                else:
                    logger.warning("[LIVE PIPELINE] Frame read failed. Marking camera health as degraded.")
                    health_tracker.record_frame(processed=False, detection_success=False)
                    time.sleep(0.1)
                    continue

            health_tracker.record_frame(processed=True, detection_success=True)
            processed_frames += 1

            # 1. Feed Frame directly into RealtimeInferenceOrchestrator (runs YOLOv8 + ByteTrack + Risk + AI)
            t_orch_start = time.time()
            inference_result = orchestrator.process_frame(
                frame,
                camera_id=camera_id,
                zone_id=zone_id,
                event_id=event_id,
                timestamp=metadata.timestamp,
                frame_id=metadata.frame_id,
                processing_mode="LIVE"
            )
            orch_latency_ms = (time.time() - t_orch_start) * 1000.0
            cv_latency_ms = orch_latency_ms
            telemetry = inference_result.get("telemetry", {}) if isinstance(inference_result, dict) else getattr(inference_result, "telemetry", {})
            total_step_latency_ms = (time.time() - t0) * 1000.0
            latencies.append(total_step_latency_ms)

            # 3. Store result in RealtimeInferenceResultStore
            result_store.update_result(inference_result)

            # 4. Optional WebSocket Broadcast
            if broadcast and realtime_stream_manager is not None:
                payload = inference_result.to_dict() if hasattr(inference_result, "to_dict") else inference_result
                # Note: async broadcast called synchronously in CLI or via loop
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(realtime_stream_manager.broadcast_inference_update(event_id, camera_id, zone_id, payload))
                    else:
                        loop.run_until_complete(realtime_stream_manager.broadcast_inference_update(event_id, camera_id, zone_id, payload))
                except Exception as e:
                    pass

            # 5. Evaluate Incident Policy Engine
            if isinstance(inference_result, dict):
                warning_info = inference_result.get("warning", {})
                operational_state = warning_info.get("operational_warning_state", "WARMING_UP")
                risk_info = inference_result.get("current_risk", {})
                physics_risk = float(risk_info.get("score") or risk_info.get("current_physics_risk") or 0.0)
                ai_info = inference_result.get("ai_prediction", {})
                ai_prob = ai_info.get("probability")
            else:
                operational_state = getattr(inference_result, "operational_warning_state", "WARMING_UP")
                physics_risk = getattr(inference_result, "current_physics_risk", 0.0)
                ai_prob = getattr(inference_result, "early_warning_probability", None)

            should_trigger = evaluate_incident_policy(operational_state)
            inc_str = f"POLICY TRIGGERED ({operational_state})" if should_trigger else "NO INCIDENT TRIGGER"

            # Log step summary every 10 frames
            if processed_frames % 10 == 0 or processed_frames == 1:
                prob_str = f"{ai_prob:.3f}" if isinstance(ai_prob, float) else "N/A (Warming Up)"
                logger.info(
                    f"[FRAME {processed_frames:04d}] Mode={cam_source.source_type} | "
                    f"Persons={telemetry.get('person_count', 0)} | Risk={physics_risk:.1f} | "
                    f"AI Prob={prob_str} | State={operational_state} | Incident={inc_str} | "
                    f"Latency={total_step_latency_ms:.1f}ms (CV:{cv_latency_ms:.1f}ms, Orch:{orch_latency_ms:.1f}ms)"
                )

            # Realtime FPS throttling if requested
            if realtime and cam_source.fps > 0:
                frame_delay = 1.0 / cam_source.fps
                time.sleep(max(0.001, frame_delay - (time.time() - t0)))

    finally:
        cam_source.release()

    elapsed = max(0.001, time.time() - start_time)
    avg_fps = round(processed_frames / elapsed, 2)
    avg_latency = round(np.mean(latencies), 2) if latencies else 0.0
    p95_latency = round(np.percentile(latencies, 95), 2) if latencies else 0.0

    logger.info("==========================================================")
    logger.info("LIVE PIPELINE EXECUTION SUMMARY")
    logger.info("==========================================================")
    logger.info(f"Processed Frames: {processed_frames} in {elapsed:.2f}s ({avg_fps} FPS)")
    logger.info(f"Step Latency: Average = {avg_latency} ms | P95 = {p95_latency} ms")
    logger.info("==========================================================")

    return {
        "status": "SUCCESS",
        "processed_frames": processed_frames,
        "elapsed_sec": round(elapsed, 2),
        "fps": avg_fps,
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95_latency
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CrowdShield Phase 6E Live Video Pipeline Runner")
    parser.add_argument("--source", type=str, choices=["video", "webcam", "rtsp"], default="video", help="Input mode")
    parser.add_argument("--video", type=str, default=None, help="Path to input video file")
    parser.add_argument("--camera-index", type=int, default=0, help="Webcam device index")
    parser.add_argument("--url", type=str, default=None, help="RTSP stream URL")
    parser.add_argument("--event-id", type=str, default="EVT-LIVE-01", help="Event ID")
    parser.add_argument("--camera-id", type=str, default="CAM-LIVE-01", help="Camera ID")
    parser.add_argument("--zone-id", type=str, default="22222222-2222-2222-2222-222222222222", help="Zone ID UUID")
    parser.add_argument("--realtime", action="store_true", help="Throttle playback to match native video FPS")
    parser.add_argument("--max-frames", type=int, default=0, help="Max frames to process (0 = all)")
    parser.add_argument("--broadcast", action="store_true", help="Enable WebSocket broadcast")
    args = parser.parse_args()

    run_live_pipeline(
        source_type=args.source,
        video_path=args.video,
        camera_index=args.camera_index,
        rtsp_url=args.url,
        event_id=args.event_id,
        camera_id=args.camera_id,
        zone_id=args.zone_id,
        realtime=args.realtime,
        max_frames=args.max_frames,
        broadcast=args.broadcast
    )
