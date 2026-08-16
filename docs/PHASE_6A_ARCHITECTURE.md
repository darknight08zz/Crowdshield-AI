# Phase 6A — System Architecture & Dependency Flow

**Repository:** `darknight08zz/CrowdShield`  
**Phase:** 6A — Real-Time Backend Inference Orchestration  
**Status:** ARCHITECTURE DISCOVERY COMPLETE  

---

## 1. Discovered Component Inventory

| System Layer | Subsystem / File | Key Responsibilities | Canonical Schema / Contract |
| :--- | :--- | :--- | :--- |
| **Camera Ingestion** | `backend/app/ingestion/cv/camera_source.py` | Abstract `CameraSource` (`VideoFileSource`, `WebcamSource`, `RTSPSource`). Reads raw frames and produces `FrameMetadata`. | `FrameMetadata(camera_id, frame_id, timestamp, fps, width, height, source_type)` |
| **CV Perception** | `backend/app/ingestion/cv/pipeline.py` | `CVPipelineManager` orchestrating `FrameSampler`, `PersonDetector` (YOLOv8), `ByteTracker`, `LineCrossingDetector`, `GateFlowRateAggregator`, `metrics.py`. | Canonical Telemetry Record (ISO timestamp, density, speed, inflow/outflow, blockage, behavior classification) |
| **Camera Health** | `backend/app/ingestion/cv/camera_health.py` | `CameraHealthTracker` & `CameraHealthRecord`. Evaluates `ONLINE`, `DEGRADED`, `OFFLINE`, `CV_UNAVAILABLE`. | Camera health status dictionary with degradation reasons and frame rate metrics |
| **Physics Risk Engine** | `backend/app/ai/dataset/temporal_feature_extractor.py` & `backend/app/core/risk_levels.py` | `compute_row_physics_risk()` (0–100 score) & `get_risk_bucket()` (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`). | Instantaneous ground truth physics risk score & standardized taxonomy bucket |
| **Temporal Extractor** | `backend/app/ai/dataset/temporal_feature_extractor.py` | `extract_temporal_derivatives_and_accelerations()`. Computes 1st/2nd order derivatives, rolling mean/std. | Canonical V2 Feature Vector (`CANDIDATE_TEMPORAL_FEATURES`) |
| **AI Model Inference** | `backend/app/ai/model_loader.py` | `load_registered_model()`, `validate_feature_vector()`, `predict_risk_probability()` (`v1.0.0`), `predict_temporal_early_warning()` (`v2.0.0`). | Model probability prediction payload (`status`, `calibrated_probability`, `target`, `is_degraded`) |
| **Alert Decision Engine** | `backend/app/ai/services/early_warning_engine.py` | `EarlyWarningEngine`. Applies $N=3$ persistence rule and $0.15$ hysteresis margin to determine operational alert state. | Operational decision dictionary (`operational_warning_state`: `WARMING_UP`, `DEGRADED`, `NORMAL`, `WATCH`, `EARLY_WARNING`, `HIGH_RISK`) |

---

## 2. Real-Time End-to-End Inference Dependency Flow

```
+-----------------------------------------------------------------------------------+
|                            VIDEO FRAME INPUT SOURCE                               |
|        VideoFileSource (MP4/DEMO) | WebcamSource (WEBCAM) | RTSPSource (RTSP)     |
+-----------------------------------------------------------------------------------+
                                          |
                                          | Frame (numpy array) + FrameMetadata
                                          v
+-----------------------------------------------------------------------------------+
|                        CV PIPELINE MANAGER (Phase 2)                              |
|   - PersonDetector (YOLOv8 person class)                                          |
|   - ByteTracker (Track IDs & velocities)                                          |
|   - LineCrossingDetector & FlowAggregator                                         |
|   - Spatial Density & Speed metrics                                               |
+-----------------------------------------------------------------------------------+
                                          |
                                          | Canonical Telemetry Record (dict)
                                          v
+-----------------------------------------------------------------------------------+
|                     REALTIME INFERENCE ORCHESTRATOR (Phase 6A)                    |
|                                                                                   |
|  1. Ingests telemetry & evaluates CameraHealthTracker state                      |
|  2. Evaluates Phase 3 Physics Risk (0-100 & LOW/MODERATE/HIGH/CRITICAL bucket)    |
|  3. Pushes telemetry to TemporalBuffer[(event_id, camera_id, zone_id)]            |
|  4. Checks warm-up status (requires >= 30 steps):                                 |
|      - If < 30: operational_warning_state = "WARMING_UP"                          |
|      - If >= 30: Extracts temporal derivatives & rolling features               |
|  5. Evaluates Model Loader v2.0.0 inference (or returns AI_UNAVAILABLE/DEGRADED)  |
|  6. Passes AI probability to EarlyWarningEngine (N=3 persistence, 0.15 margin)    |
|  7. Assembles unified RealtimeInferenceResult                                     |
+-----------------------------------------------------------------------------------+
                                          |
                                          | RealtimeInferenceResult
                                          v
+-----------------------------------------------------------------------------------+
|                         DOWNSTREAM CONSUMERS (Phase 6B+)                          |
|                  (WebSocket Broadcast / API Service / Dashboard UI)               |
+-----------------------------------------------------------------------------------+
```

---

## 3. Strict Boundary Protection & Scoping

To prevent cross-stream context leakage, temporal history buffers are explicitly scoped by composite tuple key:

$$\text{StreamKey} = (\text{event\_id}, \text{camera\_id}, \text{zone\_id})$$

* **Isolation Guarantee:** No observations from `Camera A` or `Event X` will ever contaminate the rolling sequence window of `Camera B` or `Event Y`.
* **Bounded Memory:** Each stream buffer retains a maximum of 60 historical entries. Older entries are discarded FIFO. Stale streams (inactive for $> 300\text{s}$) are automatically pruned.
