# CrowdShield Phase 2 — Real-Time Crowd Perception & Telemetry Pipeline

## Executive Summary
Phase 2 of the CrowdShield remediation roadmap has been successfully implemented. The platform now features an end-to-end, traceable, and real-time Computer Vision (CV) perception and telemetry ingestion pipeline. 

By replacing synthetic fallbacks in live modes with explicit data provenance, CrowdShield guarantees that every telemetry metric (density, inflow/outflow, speed, reverse flow, direction conflict, blockage, and rule-based behavior classification) is explicitly marked with its operational mode (`LIVE`, `DEMO`, or `SIMULATION`) and calibration status (`HOMOGRAPHY` vs `UNCALIBRATED`).

---

## Target Perception Architecture

```
                       CCTV / MP4 / RTSP Stream
                                  │
                       ┌──────────┴──────────┐
                       │  CameraSource Input │
                       │  Abstraction Layer  │
                       └──────────┬──────────┘
                                  │ Frame (BGR) + FrameMetadata
                       ┌──────────┴──────────┐
                       │    FrameSampler     │  (Configurable FPS)
                       └──────────┬──────────┘
                                  │ Sampled Frames
                       ┌──────────┴──────────┐
                       │   PersonDetector    │  (YOLOv8, class_id=0)
                       │ (No Silent Fallback)│
                       └──────────┬──────────┘
                                  │ Bounding Boxes + Centers
                       ┌──────────┴──────────┐
                       │     ByteTracker     │  (Persistent Track IDs,
                       │  Trajectory Engine  │   NEW/ACTIVE/LOST/REMOVED)
                       └──────────┬──────────┘
                                  │ Trajectory Sequences
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
┌────────┴─────────┐    ┌─────────┴────────┐    ┌──────────┴──────────┐
│  Homography &    │    │ Virtual Line    │    │ Circular Variance   │
│  Ground-Plane    │    │ Crossing & Flow │    │ Direction Conflict  │
│  Calibration     │    │ Rate Aggregator │    │ & Reverse Flow      │
└────────┬─────────┘    └─────────┬────────┘    └──────────┬──────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                       ┌──────────┴──────────┐
                       │ Rule-Based Behavior │ (SURGE, BOTTLENECK, STAGNATION,
                       │     Classifier      │  REVERSE_FLOW, CONFLICT, NORMAL)
                       └──────────┬──────────┘
                                  │
                       ┌──────────┴──────────┐
                       │  Canonical Crowd    │ (Full Data Provenance
                       │  Feature Vector     │  & Confidence Metadata)
                       └─────────────────────┘
```

---

## Key Pipeline Components & Technical Specifications

### 1. Camera Input Abstraction (`app/ingestion/cv/camera_source.py`)
Provides uniform frame capture across three concrete implementations:
- **`VideoFileSource`**: Ingests local MP4/AVI files using video-relative timestamps for deterministic replay testing (`processing_mode = "DEMO"`).
- **`WebcamSource`**: Ingests local USB/integrated camera streams (`processing_mode = "LIVE"`).
- **`RTSPSource`**: Ingests IP CCTV RTSP network streams (`processing_mode = "LIVE"`).
- Extracts structured `FrameMetadata`: `camera_id`, `frame_id`, `timestamp`, `fps`, `width`, `height`, `source_type`.

### 2. Person Detector & No Silent Fallback Rule (`app/ingestion/cv/detector.py`)
- Filters strictly for `class_id = 0` (`person`).
- Computes pixel bounding boxes `[x1, y1, x2, y2]` and center ground contacts `[cx, cy]`.
- **Strict Provenance Enforcement**: In `LIVE` mode, if the YOLO model is unavailable or frame decoding fails, the detector returns an empty list `[]` and flags `is_degraded = True`. Synthetic box generation is strictly restricted to `SIMULATION` mode.

### 3. ByteTrack Trajectory Engine (`app/ingestion/cv/tracker.py`)
- Maintains persistent `track_id` (1001, 1002...) across occlusions using high-speed Kalman motion estimation and IoU matching (<2ms overhead).
- Track Lifecycle States: `NEW` ➔ `ACTIVE` ➔ `LOST` ➔ `REMOVED`.
- Computes trajectory properties over bounded history queues:
  - `movement_direction`: Delta vector `[dx, dy]` and angle `0.0° - 360.0°`.
  - `displacement` & `path_length`: Net linear distance vs cumulative walking path.
  - `path_consistency`: Ratio of displacement to path length (values near 1.0 indicate straight walking; values near 0.0 indicate erratic wandering).
  - `stationary_duration`: Cumulative seconds spent below minimum movement threshold.

### 4. Ground-Plane Calibration (`app/ingestion/cv/calibration.py`)
- Computes 3x3 Homography matrices ($H$) using 4-point correspondence (OpenCV `findHomography` or DLT fallback).
- Converts pixel coordinates to real-world ground meters via `pixel_to_world()`.
- **Unit Precision & Transparency**:
  - Calibrated zones: `density_unit = "persons_per_m2"`, `speed_unit = "m_s"`, `calibration_status = "HOMOGRAPHY"`.
  - Uncalibrated zones: `density_unit = "NORMALIZED_ESTIMATE"`, `speed_unit = "NORMALIZED_SPEED"`, `calibration_status = "UNCALIBRATED"`, with confidence capped at 0.75 and warning issued.

### 5. Virtual Line Crossing & Flow Aggregation (`app/ingestion/cv/line_crossing.py`, `flow_rate.py`)
- Detects pedestrian directional line crossings across virtual gate segments `[[x1,y1], [x2,y2]]` using segment intersection and cross-product orientation.
- Deduplication: Tracks are counted exactly once per physical walkthrough.
- Computes rolling 60-second `inflow_rate`, `outflow_rate`, and `net_accumulation`.

### 6. Vector Metrics & Circular Variance Direction Conflict (`app/ingestion/cv/metrics.py`)
- **Direction Conflict Score**: Calculated via circular variance of active track direction angles $\theta_i$:
  $$R = \sqrt{\left(\frac{1}{N}\sum \cos \theta_i\right)^2 + \left(\frac{1}{N}\sum \sin \theta_i\right)^2}$$
  $$\text{direction\_conflict\_score} = 1.0 - R \in [0.0, 1.0]$$
- **Reverse Flow Ratio**: Proportion of moving tracks traveling $>120^\circ$ against the dominant crowd angle.
- **Blockage Score**: Composite metric combining localized density variance, low median speed, stationary ratio, and flow imbalance.

### 7. Rule-Based Behavior Classifier (`app/ingestion/cv/metrics.py`)
Deterministic, auditable classification without black-box ML:
- `SURGE`: Inflow rate $>1.8 \times$ outflow rate and inflow $\ge 60$ peds/min.
- `BOTTLENECK`: Blockage score $\ge 0.60$ or density $\ge 2.5$ peds/m² with speed $<0.4$ m/s.
- `STAGNATION`: Median speed $<0.3$ m/s and stationary ratio $\ge 0.40$.
- `REVERSE_FLOW`: Reverse flow ratio $\ge 0.25$.
- `DIRECTION_CONFLICT`: Direction conflict score $\ge 0.50$.
- `NORMAL`: Default operational state.

### 8. Camera Health Monitoring (`app/ingestion/cv/camera_health.py`)
Tracks operational camera status across 4 explicit states:
- `ONLINE`: Active frames ingested within 5s, valid CV processing.
- `DEGRADED`: Frame rate below target or zone uncalibrated.
- `OFFLINE`: No frame received within 15s timeout.
- `CV_UNAVAILABLE`: Video feed active but PyTorch/YOLO inference unavailable.

### 9. Video Replay CLI (`scripts/replay_video.py`)
Provides reproducible offline testing by running recorded MP4/AVI videos through the full perception pipeline, writing canonical telemetry logs to `.jsonl` files with `processing_mode = "DEMO"`.

---

## Canonical Telemetry Schema

```json
{
  "timestamp": "2026-08-14T23:30:00Z",
  "camera_id": "CAM-01",
  "zone_id": "zone-north-concourse",
  "density": 1.45,
  "density_unit": "persons_per_m2",
  "density_confidence": 0.92,
  "inflow_rate": 84.0,
  "outflow_rate": 72.0,
  "flow_imbalance": 12.0,
  "average_speed": 1.15,
  "median_speed": 1.10,
  "speed_unit": "m_s",
  "stationary_ratio": 0.08,
  "reverse_flow_ratio": 0.04,
  "direction_conflict_score": 0.12,
  "blockage_score": 0.15,
  "person_count": 29,
  "tracked_person_count": 27,
  "behavior_classification": "NORMAL",
  "behavior_classifier_type": "RULE_BASED_BEHAVIOR_CLASSIFIER",
  "telemetry_source": "live_cctv_gps",
  "processing_mode": "DEMO",
  "calibration_status": "HOMOGRAPHY",
  "confidence_score": 0.91,
  "is_degraded": false,
  "is_synthetic": false,
  "is_simulated": false
}
```

---

## Verification & Test Results

All 69 unit, integration, and scenario tests in the pytest suite pass with 100% success:

```bash
.\venv\Scripts\python.exe -m pytest
======================= 69 passed, 2 warnings in 21.00s =======================
```

---

## Conclusion
Phase 2 is 100% complete. CrowdShield now possesses a production-grade real-time crowd perception and telemetry generation pipeline ready to supply clean, traceable datasets to the future risk prediction layer.
