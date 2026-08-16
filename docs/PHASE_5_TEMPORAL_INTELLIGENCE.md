# Phase 5 — Temporal Early-Warning Intelligence Report

## Executive Summary
Phase 5 evolves CrowdShield AI from a static physics-proxy lookup into a **Temporal Early-Warning Intelligence System**.

Rather than predicting whether current physics formulas cross a threshold at $t$, Phase 5 models forecast the **trajectory of crowd deterioration** across future time windows ($[t + 10\text{s} \dots t + 300\text{s}]$), providing actionable early warning lead time to emergency responders before critical crowd density or pressure thresholds are reached.

---

## Key Achievements & Implementation Details

### 1. Target Redesign (Moving Beyond Static Physics Proxies)
We formulated and evaluated three candidate temporal targets:
*   **Target A: `RISK_DELTA_5M`** (Continuous escalation velocity): $R(t + 300\text{s}) - R(t)$.
*   **Target B: `EARLY_ESCALATION_5M` (Primary Target)**: Binary dynamic deterioration indicator derived from trajectory escalation:
    *   $\Delta \text{Density} \ge +0.20$ AND $\Delta \text{Speed} \le -0.25$ AND Flow Imbalance $\ge 20.0$ AND $\Delta \text{Physics Risk} \ge +15.0$, OR
    *   Transition from low risk ($R(t) < 50$) to extreme risk ($R(t+\Delta t) \ge 75$).
*   **Target C: `RISK_AT_5M`**: Continuous future risk score at $t + 300\text{s}$.

### 2. Dataset V2 Architecture & Boundary Protection
*   **Canonical Schema V2**: Defined in `backend/app/ai/dataset/schema_v2.py`.
*   **Temporal Derivative Features**: 1st & 2nd order derivatives (`density_rate`, `density_acceleration`, `speed_rate`, `speed_acceleration`, `inflow_change`, `outflow_change`, `rolling_density_mean`, `rolling_density_std`).
*   **Strict Boundary Protection**: Feature extraction and windowing strictly enforce event, camera, and zone boundaries. Sequences never cross event boundaries, eliminating cross-partition data leakage.
*   **Multi-Event Compatibility**: Built-in support for event-level grouping (`event_id`). If $\ge 2$ independent events exist, event-level splitting is executed. In the current 1-event setup, chronological splitting is strictly enforced with explicit metadata recording:
    ```json
    "generalization_status": "INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION"
    ```

### 3. Candidate Model Evaluation & Lead Time Analysis
*   **Model 1: Temporal XGBoost Baseline (Selected)**
    *   Optimal Validation Threshold: `0.0500`
    *   Test F1: **0.6667**
    *   Test PR-AUC: **1.0000**
    *   Test Accuracy: **0.9938**
    *   False Alarm Rate: **0.62%**
    *   Top Feature Importances: `net_accumulation` (10.1%), `density_rate` (8.2%), `person_count` (7.2%), `reverse_flow_ratio` (7.1%), `outflow_rate` (7.1%), `speed_change` (5.6%).
*   **Model 2: Temporal Sequence GRU Baseline**
    *   Test PR-AUC: `0.0333` (Flat sequence representation requires multi-event scaling).
*   **Model 3: Temporal Transformer Justification**
    *   Dataset size check ($N = 1080 < 2000$) resulted in explicit status:
        `"TRANSFORMER_NOT_JUSTIFIED_BY_DATA_SIZE"`.
*   **Early-Warning Lead Time**:
    *   **Mean Lead Time**: **29.3 seconds** advance warning before crowd deterioration occurs.

### 4. Operational Alert Stability & Decision Engine
Implemented `EarlyWarningEngine` (`backend/app/ai/services/early_warning_engine.py`) supporting:
*   Operational Alert States: `NORMAL`, `WATCH`, `EARLY_WARNING`, `HIGH_RISK`.
*   $N$-step Persistence Rule: Requires $N=3$ consecutive high probability readings (30s) to upgrade state.
*   Hysteresis Margin (0.15): Prevents rapid alert flickering during minor sensor noise.

### 5. Model Registry & Model Provenance
*   **Version `v1.0.0_20260814_202414`**: Preserved untouched as `PROXY_BASELINE`.
*   **Version `v2.0.0`**: Registered as active temporal early-warning model under `backend/app/ai/models/risk/v2.0.0/`.
*   **Explicit Provenance Tags**:
    ```json
    {
      "model_version": "v2.0.0",
      "model_status": "PROTOTYPE",
      "label_type": "PROXY",
      "ground_truth_status": "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
      "generalization_status": "INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION"
    }
    ```

---

## Artifact Locations
*   **Schema V2**: `backend/app/ai/dataset/schema_v2.py`
*   **Temporal Extractor**: `backend/app/ai/dataset/temporal_feature_extractor.py`
*   **Dataset Builder V2**: `backend/app/ai/dataset/builder_v2.py`
*   **Temporal Trainer**: `backend/app/ai/training/temporal_trainer.py`
*   **Early Warning Engine**: `backend/app/ai/services/early_warning_engine.py`
*   **Model Registry**: `backend/app/ai/training/model_registry.py` & `backend/app/ai/models/risk/v2.0.0/`
*   **Phase 5 Execution Report**: `data/training_reports/phase5_temporal_report.json`
*   **Unit Tests**: `backend/tests/test_phase5_temporal.py` (All 6 tests passed)
