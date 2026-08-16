# Phase 4A — Crowd Risk Model Integrity Audit Report

## Executive Summary
This document provides the complete integrity audit of CrowdShield's Phase 4 machine learning training and evaluation pipeline. Following the reported **~98.9% F1-score** across Logistic Regression, Random Forest, and XGBoost models on the Phase 3 dataset, this audit was conducted to investigate data leakage, feature circularity, threshold optimization, prediction array uniqueness, rule baseline mechanics, and cross-event generalization.

---

## Final Verdict

### Verdict: `B. PROXY_LEARNING_VALID_BUT_NOT_GENERALIZABLE`

> [!IMPORTANT]
> **Summary Verdict Interpretation:**
> 1. **No Data Leakage:** The 98.88% F1-score is **NOT** caused by direct target leakage or future-timestamp information leakage.
> 2. **Circular Proxy Learning:** The ML models are learning to reproduce the deterministic physics risk state transition boundary (`compute_row_physics_risk >= 70.0`) directly from the physical telemetry features (`density`, `speed`, `tracked_person_count`, `blockage_score`).
> 3. **Rule Baseline Parity:** When evaluated using the rule engine's 5-minute projection (`risk_5min`), the deterministic physics baseline achieves the **exact same 98.88% F1-score** on the test set.
> 4. **Event Independence Limitation:** The dataset contains 1,200 samples originating from **1 unique event** across 4 zones. While the model is valid as a proxy-learning prototype, cross-event real-world generalization cannot be measured until multi-event telemetry is available.

---

## Required Checklist & Diagnostic Flag Summary

| Diagnostic Flag | Status / Result | Findings / Notes |
| :--- | :---: | :--- |
| **DIRECT LEAKAGE** | **NO** | Zero target-derived or label columns present in feature matrix $X$. |
| **FUTURE DATA LEAKAGE** | **NO** | Temporal windowing strictly uses observations at timestamp $\le t$. |
| **CIRCULAR PROXY LEARNING** | **YES** | ML models learn to predict physics rule target from physical telemetry features. |
| **RULE BASELINE BUG** | **NO** | 0.70 threshold on current risk was conservative; 5-min projected risk yields 98.88% F1. |
| **THRESHOLD BUG** | **NO** | Selected validation threshold (0.10) maps to clean separation interval. |
| **PREDICTION ARRAY BUG** | **NO** | Prediction arrays across LR, RF, and XGBoost have unique SHA-256 hashes. |
| **TEST SET LEAKAGE** | **NO** | Test set (180 samples) remained untouched during training and threshold tuning. |
| **INDEPENDENT EVENTS** | **1 Event** | 1,200 rows sampled across 1 event, 2 cameras, 4 zones. |
| **EVENT-LEVEL VALIDATION** | **INSUFFICIENT** | LOGO cross-validation requires $\ge 2$ independent events. |
| **CALIBRATION** | **AUDITED** | Platt scaling calibrated probabilities; test Brier score = 0.0136. |

---

## 1. Exact Data Flow Trace
```
Raw Telemetry Log
      ↓
Provenance Filter (MIXED_EXPLICIT)
      ↓
Missing Telemetry Handler (Forward Fill / Safe Imputation)
      ↓
Chronological Sort by Zone & Timestamp
      ↓
Temporal Feature Windowing (Only rows <= timestamp t)
      ↓
Target Horizon Assignment (Max risk in window [t + 10s to t + 300s])
      ↓
Leakage-Free Splitting (Train 70% [840], Val 15% [180], Test 15% [180])
      ↓
Standard Scaler Fitting (Strictly on Train Split)
      ↓
Model Fitting & Val Threshold Tuning
      ↓
Val Platt Calibration Fitting
      ↓
Untouched Test Set Evaluation
```

---

## 2. Target Generation Audit

The prediction target `HIGH_RISK_WITHIN_5M` is defined as:
```python
def compute_row_physics_risk(row: pd.Series) -> float:
    density = float(row.get("density", 0.4))
    speed = float(row.get("average_speed", 1.2))
    inflow = float(row.get("inflow_rate", 80.0))
    outflow = float(row.get("outflow_rate", 80.0))
    conflict = float(row.get("direction_conflict_score", 0.15))
    incidents = float(row.get("recent_incident_count_10min", 0.0))
    reverse_flow = float(row.get("reverse_flow_ratio", 0.05))
    blockage = float(row.get("blockage_score", 0.10))

    flow_delta_ratio = np.clip((inflow - outflow) / max(outflow, 30.0), -1.0, 2.0)

    base_risk = (
        (density ** 2) * 42.0 +
        max(0.0, 1.0 - speed) * 16.0 +
        max(0.0, flow_delta_ratio) * 16.0 +
        conflict * 10.0 +
        incidents * 6.0 +
        reverse_flow * 10.0 +
        blockage * 10.0
    )
    return float(np.clip(base_risk, 0.0, 100.0))

# Target label assignment looking forward from index t:
fut_5m_max = max(precomputed_risk_scores[t+1 : t+30])
HIGH_RISK_WITHIN_5M = 1 if fut_5m_max >= 70.0 else 0
```

---

## 3. Feature Origin Audit Table

| Feature Name | Source | Derived From Risk? | Future Data? | Safe? |
| :--- | :--- | :---: | :---: | :---: |
| `density` | CV Bounding Boxes / Area | No | No | Yes |
| `inflow_rate` | Boundary Crossing Tracker | No | No | Yes |
| `outflow_rate` | Boundary Crossing Tracker | No | No | Yes |
| `average_speed` | Optical Flow / ByteTrack | No | No | Yes |
| `median_speed` | Optical Flow / ByteTrack | No | No | Yes |
| `stationary_ratio` | Speed Threshold Filter | No | No | Yes |
| `reverse_flow_ratio` | Trajectory Vector Angles | No | No | Yes |
| `direction_conflict_score` | Flow Vector Dispersal | No | No | Yes |
| `blockage_score` | Spatial Grid Accumulation | No | No | Yes |
| `person_count` | YOLO Detection Count | No | No | Yes |
| `tracked_person_count` | ByteTrack Active IDs | No | No | Yes |
| `flow_imbalance` | `inflow - outflow` | No | No | Yes |
| `net_accumulation` | `inflow - outflow` | No | No | Yes |
| `density_change` | $t - (t-1)$ Delta | No | No | Yes |
| `density_rate` | $t - (t-1)$ Rate | No | No | Yes |
| `speed_change` | $t - (t-1)$ Delta | No | No | Yes |
| `speed_rate` | $t - (t-1)$ Rate | No | No | Yes |
| `inflow_change` | $t - (t-1)$ Delta | No | No | Yes |
| `outflow_change` | $t - (t-1)$ Delta | No | No | Yes |
| `rolling_density_mean` | Rolling 5-row Mean ($\le t$) | No | No | Yes |
| `rolling_density_std` | Rolling 5-row Std ($\le t$) | No | No | Yes |
| `rolling_speed_mean` | Rolling 5-row Mean ($\le t$) | No | No | Yes |
| `rolling_speed_std` | Rolling 5-row Std ($\le t$) | No | No | Yes |

---

## 4. Feature-Target Association Audit

| Feature | Pearson $r$ | Spearman $r$ | Positive Mean ($Y=1$) | Negative Mean ($Y=0$) |
| :--- | :---: | :---: | :---: | :---: |
| `tracked_person_count` | +0.9219 | +0.7577 | 60.66 | 11.85 |
| `density` | +0.9224 | +0.7570 | 0.8122 | 0.1649 |
| `average_speed` | -0.9278 | -0.7573 | 0.3922 | 1.2608 |
| `blockage_score` | +0.9244 | +0.7599 | 0.5686 | 0.1180 |
| `direction_conflict_score` | +0.9238 | +0.7589 | 0.6092 | 0.1256 |
| `stationary_ratio` | +0.9230 | +0.7600 | 0.4061 | 0.0829 |
| `flow_imbalance` | +0.9216 | +0.7564 | 108.23 | -65.46 |
| `rolling_density_mean` | +0.9224 | +0.7568 | 0.8069 | 0.1640 |
| `rolling_speed_mean` | -0.9281 | -0.7569 | 0.3992 | 1.2623 |

---

## 5. Single-Feature Ablation Experiments

To test whether performance collapses upon removing any single feature, each suspicious feature was individually ablated from the model:

| Ablated Feature | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Test Brier Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **None (Full Model)** | 0.9889 | 0.9778 | 1.0000 | 0.9888 | 0.9890 | 0.0136 |
| `density` | 0.9889 | 0.9778 | 1.0000 | 0.9888 | 0.9891 | 0.0136 |
| `density_rate` | 0.9889 | 0.9778 | 1.0000 | 0.9888 | 0.9880 | 0.0136 |
| `flow_imbalance` | 0.9889 | 0.9778 | 1.0000 | 0.9888 | 0.9880 | 0.0136 |
| `blockage_score` | 0.9889 | 0.9778 | 1.0000 | 0.9888 | 0.9880 | 0.0136 |
| `speed_change` | 0.9889 | 0.9778 | 1.0000 | 0.9888 | 0.9880 | 0.0136 |
| `stationary_ratio` | 0.9889 | 0.9778 | 1.0000 | 0.9888 | 0.9891 | 0.0136 |
| `direction_conflict_score` | 0.9889 | 0.9778 | 1.0000 | 0.9888 | 0.9880 | 0.0136 |
| `reverse_flow_ratio` | 0.9889 | 0.9778 | 1.0000 | 0.9888 | 0.9880 | 0.0136 |

---

## 6. Baseline Rule Engine Evaluation Audit

The rule baseline evaluation was audited under two configurations:

1. **Current Risk Score at $t$ (`current_risk / 100.0` @ 0.70 threshold):**
   - Precision: `0.0000`, Recall: `0.0000`, F1: `0.0000`, ROC-AUC: `0.9875`.
   - *Reason:* At time $t$, before escalation occurs 5 minutes later, current risk is ~45.0–55.0. A strict threshold of 0.70 at time $t$ yields 0 positives.
2. **5-Minute Projected Risk (`risk_5min / 100.0` @ 0.70 threshold or Current Risk @ 0.40 threshold):**
   - Precision: **`0.9778`**, Recall: **`1.0000`**, F1: **`0.9888`**, ROC-AUC: **`0.9930`**.
   - *Conclusion:* The physics rule engine's projected risk matches the ML model performance perfectly on this dataset, confirming **Circular Proxy Learning**.

---

## 7. Validation Threshold Sweep ($0.05 \dots 0.90$)

Tuned strictly on the **Validation Split** (180 samples):

| Threshold | Validation Precision | Validation Recall | Validation F1 | Validation FPR | Validation FNR |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0.05 | 0.5000 | 1.0000 | 0.6667 | 1.0000 | 0.0000 |
| **0.10 (Selected)** | **1.0000** | **1.0000** | **1.0000** | **0.0000** | **0.0000** |
| 0.20 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| 0.30 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| 0.50 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| 0.70 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| 0.90 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |

---

## 8. Prediction Probability Distribution Audit (Test Set)

| Metric | Negative Class ($Y=0$, $N=92$) | Positive Class ($Y=1$, $N=88$) |
| :--- | :---: | :---: |
| **Min Probability** | 0.0615 | 0.9383 |
| **Max Probability** | 0.9383 | 0.9383 |
| **Mean Probability** | 0.0809 | 0.9383 |
| **Median Probability** | 0.0618 | 0.9383 |
| **Std Dev** | 0.1278 | 0.0000 |

---

## 9. Model Comparison & Prediction Array Integrity

Prediction arrays were verified across models on the test set:
- **Logistic Regression Hash:** `1ead4237446755cf`
- **Random Forest Hash:** `ff695337d2cec1f5`
- **XGBoost Hash:** `d74514bed8a31046`
- **Integrity Status:** **`arrays_are_unique = True`** (Models evaluate independent predictions without array caching or variable reuse).

---

## 10. Calibration Audit

- **Raw Test Brier Score:** `0.0110`
- **Calibrated Test Brier Score (Platt Scaling):** `0.0136`
- *Conclusion:* Platt scaling smooths raw tree output probabilities to continuous calibrated scores appropriate for API consumption.

---

## 11. SHAP & Feature Importance Audit

Top features driving XGBoost predictions:
1. `tracked_person_count`: 34.59%
2. `blockage_score`: 18.87%
3. `rolling_speed_mean`: 17.94%
4. `density`: 13.15%
5. `median_speed`: 9.15%

---

## 12. Unsupported Claims Audit

Search of API, documentation, and UI confirms:
- **No claims** of "real-world validation" or "stampede prevention accuracy" exist.
- System explicitly maintains: `model_status = "PROTOTYPE"`, `label_type = "PROXY"`, and `ground_truth_status = "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED"`.

---

## Audit Output Files
- **Audit Script:** `backend/scripts/audit_model_integrity.py`
- **Raw Audit Results JSON:** `backend/data/training_reports/phase4a_audit_results.json`
- **Audit Documentation Report:** `docs/PHASE_4A_MODEL_INTEGRITY_AUDIT.md`
