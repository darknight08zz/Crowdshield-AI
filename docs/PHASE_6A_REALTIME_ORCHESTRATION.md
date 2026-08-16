# Phase 6A — Real-Time AI Inference Orchestration Documentation

**Repository:** `darknight08zz/CrowdShield`  
**Phase:** 6A — Backend Real-Time Inference Orchestration  
**Status:** COMPLETE (100% Tests Passing, Replay Validated)  

---

## 1. Overview & Architecture

Phase 6A connects Phase 2 real-time CV perception, Phase 3 ground truth physics risk calculation, Phase 5 temporal feature extraction, and Phase 5B `v2.0.0` temporal model + `EarlyWarningEngine` into a unified, thread-safe in-memory stream orchestrator: `RealtimeInferenceOrchestrator`.

### Component Flow

```
Camera Input Frame / Telemetry
           ↓
CVPipelineManager (Phase 2 PersonDetector + ByteTracker)
           ↓
Canonical Telemetry Record + CameraHealthTracker Evaluation
           ↓
Phase 3 Physics Risk Score (0–100 & LOW/MODERATE/HIGH/CRITICAL)
           ↓
TemporalBuffer[(event_id, camera_id, zone_id)] (Bounded Max 60 Steps)
           ↓
History Step Evaluation:
  ├── < 30 Steps: status = "WARMING_UP", state = WARMING_UP
  └── >= 30 Steps: Temporal Feature Extractor (Derivatives/Accelerations)
           ↓
v2.0.0 Temporal Model Inference (XGBoost)
           ↓
EarlyWarningEngine (N=3 Persistence, 0.15 Hysteresis Margin)
           ↓
Unified RealtimeInferenceResult Payload
```

---

## 2. Key Architectural Guarantees & Contract

1. **Reuse of Existing Code:**
   * Reuses `CVPipelineManager` (`backend/app/ingestion/cv/pipeline.py`).
   * Reuses `CameraHealthTracker` (`backend/app/ingestion/cv/camera_health.py`).
   * Reuses `compute_row_physics_risk` & `extract_temporal_derivatives_and_accelerations` (`temporal_feature_extractor.py`).
   * Reuses `predict_temporal_early_warning` (`model_loader.py`).
   * Reuses `EarlyWarningEngine` (`early_warning_engine.py`).

2. **Stream Scoping & Boundary Protection:**
   * Scoped by composite key `(event_id, camera_id, zone_id)`.
   * Temporal buffer history is strictly isolated; no cross-stream context leakage.

3. **Separation of Risk & AI Probability:**
   * **Physics Risk:** Instantaneous ground truth score ($0.0 - 100.0$) and bucket (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`).
   * **AI Probability:** Forecast escalation probability ($0.0 - 1.0$) for 5-minute horizon (`EARLY_ESCALATION_5M`).
   * **Operational Alert State:** Evaluated by `EarlyWarningEngine` (`NORMAL`, `WATCH`, `EARLY_WARNING`, `HIGH_RISK`).

4. **Warm-Up & Failure Handling:**
   * Below 30 steps: returns `WARMING_UP` state without fake AI predictions.
   * Model failure / unreadable artifact / NaN feature: returns `ai_prediction_status = "AI_UNAVAILABLE"`, `operational_warning_state = "DEGRADED"`, `is_degraded = True`.
   * Camera offline / CV failure: returns `CAMERA_OFFLINE` / `CV_UNAVAILABLE` without fake telemetry.

5. **Bounded Memory & Performance:**
   * Buffer capacity capped at 60 entries per stream (FIFO replacement).
   * Average Orchestrator Latency: **~1.9 ms** (excluding raw YOLO detection time) / **~52.2 ms** (full end-to-end replay).

---

## 3. Replay Test & Verification Results

### Unit Test Execution (`test_phase6a_orchestrator.py`)
* **Total Scenarios Tested:** 30 / 30
* **Status:** PASS (30 passed, 0 failed, 0 errors)
* **Execution Time:** 1.94s

### Hardening Pass Regression Test (`test_phase5b_hardening.py`)
* **Total Scenarios Tested:** 12 / 12
* **Status:** PASS (12 passed, 0 failed, 0 errors)

---

## 4. Phase 6B Readiness Checklist

- [x] Backend orchestration layer implemented (`inference_orchestrator.py`).
- [x] Stream buffering, warm-up, and error isolation verified.
- [x] Provenance, disclaimers, and timestamp semantics preserved.
- [x] Zero frontend modifications introduced.
- [x] Zero WebSocket endpoints created yet (deferred to Phase 6D).
- [x] Ready for Phase 6B Live Video / Replay Integration.
