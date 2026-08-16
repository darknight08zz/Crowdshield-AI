# PHASE 3 — RISK ENGINE, DATASET & LABELING FOUNDATION

**Repository:** `darknight08zz/CrowdShield`  
**Phase Status:** Phase 0 (COMPLETE), Phase 1 (COMPLETE), Phase 2 (COMPLETE), **Phase 3 (COMPLETE)**  
**Document Date:** August 2026  

---

## 1. Executive Summary & Objective

Phase 3 establishes the **AI dataset and labeling foundation** for CrowdShield, bridging real-time Computer Vision (CV) telemetry (ingested and calculated in Phase 2) to future predictive Machine Learning (ML) models (to be trained in Phase 4).

The primary objective of Phase 3 is to construct a **scientifically defensible, reproducible, leakage-free dataset generation pipeline** while cleanly auditing and isolating the existing rule-based risk calculation engine.

### Strict Governance Rules Enforced in Phase 3
1. **NO AI MODEL TRAINING WAS PERFORMED IN PHASE 3.** Model fitting is explicitly reserved for Phase 4.
2. **NO FABRICATED STAMPEDES OR CLINICAL GROUND TRUTH.** Historical stampede incident ground-truth logs are not available in the repository. Target labels are explicitly classified as `PROXY` labels (`HIGH_RISK_STATE_TRANSITION_PROXY`) with `NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED` ground-truth status.
3. **STRICT DATA LEAKAGE PREVENTION.** Input feature extraction windows at time $t$ use *strictly* observations $\le t$. Target prediction horizons evaluate future states looking forward into $[t + 1\text{s}, t + \text{HORIZON}]$.
4. **EXPLICIT PROVENANCE ISOLATION.** Telemetry records are tagged as `LIVE`, `DEMO`, `SYNTHETIC`, or `SIMULATED`. Datasets can be built under `REAL_ONLY`, `DEMO_VIDEO`, `SYNTHETIC`, or `MIXED_EXPLICIT` filtering modes.

---

## 2. Risk Engine Audit & Decoupling

### 2.1 Audit Findings
An audit of `app/ai/risk_model.py`, `app/ai/features.py`, and `app/core/risk_levels.py` revealed:
- The current risk engine (`predict_risk`) evaluates real-time risk scores ($0.0 - 100.0$) using deterministic Fruin crowd density thresholds, bottleneck accumulation formulas, direction conflict scores, and momentum-based trajectory deltas.
- Multi-horizon outputs (`risk_2min`, `risk_5min`, `risk_10min`) returned by the live API are **momentum-based trajectory projections** derived from inflow/outflow differential ratios.
- **Decoupling Action:** Current risk inference is retained as a **deterministic baseline benchmark** (`baseline_risk` in `app/ai/dataset/baseline_engine.py`). API endpoints (`GET /zones/{zone_id}/risk`) now return `future_prediction_status = "NOT_TRAINED"`, `ai_model_prediction = null`, and explicitly label existing multi-horizon extrapolations as `rule_based_projection` with `projection_method = "PHYSICS_MOMENTUM_TRAJECTORY"`.

### 2.2 Risk State Taxonomy
Risk buckets are strictly defined in `app/core/risk_levels.py`:
- **`LOW`**: Score $0.00 - 24.99$ (Normal crowd dynamics)
- **`MODERATE`**: Score $25.00 - 49.99$ (Heightened monitoring required)
- **`HIGH`**: Score $50.00 - 74.99$ (Pre-critical escalation / active crowd control needed)
- **`CRITICAL`**: Score $75.00 - 100.00$ (Severe stampede/surge risk / immediate emergency intervention)

---

## 3. Target Problem Formulation & Horizons

### 3.1 Primary ML Objective
The future ML task is formulated as **Early Warning of High/Critical Crowd Risk Transitions**.

Given a rolling sequence window of observations up to timestamp $t$:
$$X_t = \{x_{t - W}, x_{t - W + 1}, \dots, x_t\}$$
The model predicts the probability that the zone will transition into a `HIGH` ($\ge 70.0$) or `CRITICAL` ($\ge 85.0$) risk state within a future prediction horizon $\Delta t$:
$$P\left(\max_{\tau \in (t, t + \Delta t]} \text{Risk}(\tau) \ge 70.0 \,\Big|\, X_t\right)$$

### 3.2 Standardized Prediction Horizons
- **2-Minute Horizon (`HIGH_RISK_WITHIN_2M`)**: Short-term immediate tactical warning ($120\text{ seconds}$).
- **5-Minute Horizon (`HIGH_RISK_WITHIN_5M`)**: Primary operational planning window ($300\text{ seconds}$).
- **10-Minute Horizon (`HIGH_RISK_WITHIN_10M`)**: Strategic crowd rerouting window ($600\text{ seconds}$).
- **Primary Proxy Target (`HIGH_RISK_STATE_TRANSITION_PROXY`)**: Aligned with the 5-minute prediction horizon (`HIGH_RISK_WITHIN_5M`).

---

## 4. Ground Truth & Proxy Label Strategy

### 4.1 Ground Truth Availability Notice
> [!WARNING]
> **No validated historical ground-truth stampede incident dataset exists in the local repository.**  
> Faking or hallucinating historical crowd disaster logs is strictly prohibited to prevent dangerous model bias.

### 4.2 Proxy Labeling Methodology
Target labels are generated using a deterministic physics transition proxy:
- Target $Y_t = 1$ if the maximum baseline physics risk score in the forward horizon $[t + 1\text{s}, t + \Delta t]$ reaches or exceeds $70.0$ (`HIGH` / `CRITICAL` threshold).
- Target $Y_t = 0$ otherwise.
- All target metadata retains `label_type = "PROXY"` and `ground_truth_status = "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED"`.

---

## 5. Canonical ML Feature Schema

All Phase 3 dataset outputs conform to `FEATURE_SCHEMA_VERSION = "v1.0"`, `LABEL_SCHEMA_VERSION = "v1.0"`, and `DATASET_VERSION = "v1.0"`.

| Feature Name | Category | Type | Description |
| :--- | :--- | :--- | :--- |
| `timestamp` | Identifier | String (ISO 8601) | ISO UTC timestamp of observation |
| `camera_id` | Identifier | String | Unique identifier of ingestion camera |
| `zone_id` | Identifier | String | Unique zone or sector identifier |
| `event_id` | Identifier | String | Associated event container ID |
| `density` | Raw Feature | Float ($0.0 - 1.0$) | Bounding box spatial density ratio |
| `inflow_rate` | Raw Feature | Float ($\ge 0.0$) | Inflow rate (persons/min) crossing virtual gates |
| `outflow_rate` | Raw Feature | Float ($\ge 0.0$) | Outflow rate (persons/min) exiting virtual gates |
| `average_speed` | Raw Feature | Float ($\ge 0.0$) | Average tracked pedestrian speed ($\text{m/s}$) |
| `median_speed` | Raw Feature | Float ($\ge 0.0$) | Median tracked pedestrian speed ($\text{m/s}$) |
| `stationary_ratio` | Raw Feature | Float ($0.0 - 1.0$) | Ratio of stationary vs moving tracks |
| `reverse_flow_ratio` | Raw Feature | Float ($0.0 - 1.0$) | Vector dot-product direction conflict ratio |
| `direction_conflict_score` | Raw Feature | Float ($0.0 - 1.0$) | Angular variance of crowd velocity vectors |
| `blockage_score` | Raw Feature | Float ($0.0 - 1.0$) | Physical bottleneck accumulation index |
| `person_count` | Raw Feature | Integer | Count of detected person bounding boxes |
| `tracked_person_count` | Raw Feature | Integer | Count of actively tracked ByteTrack trajectories |
| `flow_imbalance` | Derived Feature | Float | Inflow minus outflow differential rate |
| `net_accumulation` | Derived Feature | Float | Cumulative net flow rate |
| `density_change` | Derived Feature | Float | First-order density derivative ($\Delta \text{density}$) |
| `density_rate` | Derived Feature | Float | Temporal rate of density change |
| `speed_change` | Derived Feature | Float | First-order speed derivative ($\Delta \text{speed}$) |
| `speed_rate` | Derived Feature | Float | Acceleration / deceleration rate of crowd flow |
| `inflow_change` | Derived Feature | Float | Derivative of inflow rate |
| `outflow_change` | Derived Feature | Float | Derivative of outflow rate |
| `rolling_density_mean` | Derived Feature | Float | 5-sample rolling window density mean ($\mu$) |
| `rolling_density_std` | Derived Feature | Float | 5-sample rolling window density std ($\sigma$) |
| `rolling_speed_mean` | Derived Feature | Float | 5-sample rolling window speed mean ($\mu$) |
| `rolling_speed_std` | Derived Feature | Float | 5-sample rolling window speed std ($\sigma$) |
| `calibration_status` | Metadata | String | `HOMOGRAPHY`, `UNCALIBRATED`, `APPROXIMATE` |
| `telemetry_source` | Metadata | String | `live_cctv_gps`, `replay_log`, `synthetic_fallback` |
| `processing_mode` | Metadata | String | `LIVE`, `DEMO`, `SIMULATED` |
| `confidence_score` | Metadata | Float ($0.0 - 1.0$) | CV tracking & detection confidence score |
| `is_degraded` | Metadata | Boolean | True if feed is stale or fallback-imputed |
| `is_synthetic` | Metadata | Boolean | True if generated synthetically |
| `is_simulated` | Metadata | Boolean | True if from physics simulation environment |
| `HIGH_RISK_WITHIN_2M` | Target | Integer ($0$ or $1$) | Target binary label for 2-minute horizon |
| `HIGH_RISK_WITHIN_5M` | Target | Integer ($0$ or $1$) | Target binary label for 5-minute horizon |
| `HIGH_RISK_WITHIN_10M` | Target | Integer ($0$ or $1$) | Target binary label for 10-minute horizon |
| `HIGH_RISK_STATE_TRANSITION_PROXY` | Target | Integer ($0$ or $1$) | Preferred proxy target for primary model training |

---

## 6. Sequence Windowing & Leakage Prevention Rules

### 6.1 No-Future-Data Feature Rule
> [!IMPORTANT]
> **Strict Leakage Prevention Guarantee:**  
> For any sample row at timestamp $t$:
> - Feature extraction is computed strictly on telemetry rows $s \le t$.
> - Future values ($s > t$) are strictly barred from participating in rolling statistics ($\mu, \sigma$), temporal deltas ($\Delta$), or imputations.
> - Feature timestamp is recorded as $t_{\text{feature}} = t$.

### 6.2 Target Horizon Calculation Rule
- Target horizon evaluation looks forward strictly into $(t, t + \Delta t]$.
- Target evaluation window $s \in (t, t + \Delta t]$ has feature timestamp $t_{\text{target\_window}} > t$.
- Target variables are excluded from the candidate model input feature list (`CANDIDATE_MODEL_FEATURES`).

---

## 7. Telemetry Provenance & Quality Validation

### 7.1 Provenance Isolation Modes
`app/ai/dataset/provenance_filter.py` enforces explicit data isolation:
- `REAL_ONLY`: Live CCTV/GPS feeds (`is_synthetic = False`, `processing_mode = "LIVE"`).
- `DEMO_VIDEO`: Replayed CCTV footage (`is_synthetic = False`, `processing_mode = "DEMO"`).
- `SYNTHETIC`: Synthetic simulated telemetry (`is_synthetic = True`).
- `MIXED_EXPLICIT`: Retains all sources while preserving explicit provenance tags.

### 7.2 Missing & Stale Telemetry Policies (`app/ai/dataset/missing_data.py`)
- Missing identifiers (`timestamp`, `zone_id`): Sample row discarded.
- Short gaps ($\le 30$ seconds) on continuous features (`density`, `speed`, `inflow`): Linear interpolation permitted.
- Long gaps ($> 30$ seconds) or stale feeds: Marked `is_degraded = True`. Un-flagged forward filling is strictly prohibited.

### 7.3 Quality Validation Engine (`app/ai/dataset/quality_validator.py`)
Automated quality checks verify:
- Zero duplicate `(timestamp, zone_id)` keys.
- All timestamps in monotonic increasing order per zone.
- All density, speed, and flow rates within non-negative physical bounds.
- Confidence scores within $[0.0, 1.0]$.
- Reports synthetic contamination ratio and degraded feed percentage.

---

## 8. Leakage-Free Splitting & Scaling Protocol

### 8.1 Dataset Split Strategies (`app/ai/dataset/splitter.py`)
- **Row-level random splitting is strictly prohibited** for time-series telemetry.
- **`CHRONOLOGICAL` Split Strategy**:
  - `Train Set`: Earliest $70\%$ of time interval.
  - `Validation Set`: Next $15\%$ of time interval.
  - `Test Set`: Latest $15\%$ of time interval.
- **`EVENT_LEVEL` Split Strategy**:
  - Entire events or zones are assigned to `Train`, `Validation`, or `Test` splits. No event is split across train and test.

### 8.2 Non-Leaking Feature Scaling (`app/ai/dataset/scaler_prep.py`)
- Feature scaling parameters ($\mu, \sigma, \min, \max$) are computed **strictly on the `TRAIN` split**.
- Validation and Test sets are normalized using the training set parameters to prevent data leakage.

---

## 9. CLI Tools & Dataset Generation

### 9.1 Dataset Generation CLI (`scripts/build_dataset.py`)
```bash
python scripts/build_dataset.py \
  --input data/telemetry_log.csv \
  --output data/dataset_v1 \
  --window 300 \
  --horizon 300 \
  --source MIXED_EXPLICIT \
  --split CHRONOLOGICAL
```
- Performs missing data handling, provenance filtering, chronological sorting, sequence windowing, derived feature extraction, target assignment, leakage-free splitting, scaler computation, quality validation, and saves CSV dataset splits + `dataset_metadata.json`.
- **Model Training:** `NOT PERFORMED` (Phase 3 Foundation Only).

### 9.2 Dataset Inspection CLI (`scripts/inspect_dataset.py`)
```bash
python scripts/inspect_dataset.py --dataset data/dataset_v1
```
Reports total rows, train/val/test split sizes, time ranges, zone/camera counts, target class distributions, missing value counts, provenance distribution, data leakage check status (`PASS`), and model training status (`NOT_PERFORMED`).

---

## 10. Phase 3 Verification & Readiness Checklist

- [x] **Risk Engine Audit & Decoupling Complete** (`baseline_risk` interface preserved, `future_prediction_status = "NOT_TRAINED"`, `rule_based_projection` explicitly labeled).
- [x] **Target Problem & Horizons Defined** (2m, 5m, 10m horizons with primary 5m `HIGH_RISK_STATE_TRANSITION_PROXY` target).
- [x] **Ground Truth Limitations Documented** (`label_type = "PROXY"`, `ground_truth_status = "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED"`).
- [x] **Canonical ML Feature Schema Created** (`schema.py` defines Identifiers, Raw Features, Derived Features, Metadata, and Targets).
- [x] **Sequence Windowing & Temporal Extraction Built** (`feature_extractor.py` guarantees zero future feature leakage).
- [x] **Provenance Filtering Built** (`provenance_filter.py` supports `REAL_ONLY`, `DEMO_VIDEO`, `SYNTHETIC`, `MIXED_EXPLICIT`).
- [x] **Quality Validation & Missing Data Policies Built** (`quality_validator.py` and `missing_data.py`).
- [x] **Leakage-Free Splitting & Scaling Built** (`splitter.py` and `scaler_prep.py` guarantee non-leaking train/val/test splits and scalers).
- [x] **CLI Tools Operational** (`build_dataset.py` and `inspect_dataset.py` tested and validated).
- [x] **Full Automated Test Suite Passing** (80/80 backend pytest tests passing cleanly).

**Phase 3 is COMPLETE and verified. The repository is fully prepared for Phase 4 (AI Model Training & Validation).**
