# Phase 4 — Crowd Risk AI Model Training, Evaluation & Model Registry

## Overview
Phase 4 completes the transition of **CrowdShield** from a purely rule-based crowd monitoring baseline into a machine-learning-assisted predictive risk platform. This phase builds directly upon the leakage-free, temporal dataset foundation established in Phase 3.

---

## Key Achievements & Deliverables

### 1. Pre-Training Dataset Audit & Provenance Verification
- **Automated Auditor:** Created `app/ai/training/dataset_auditor.py` to audit dataset splits prior to model training.
- **Leakage Prevention:** Verified zero timestamp/zone overlap across `train`, `val`, and `test` splits.
- **Provenance Modes:** Supports `REAL_ONLY`, `DEMO_VIDEO`, `SYNTHETIC`, and `MIXED_EXPLICIT` data filtering.
- **Target Distribution:** Evaluated positive/negative class balance for multi-horizon target labels (`HIGH_RISK_WITHIN_2M`, `HIGH_RISK_WITHIN_5M`, `HIGH_RISK_WITHIN_10M`, and `HIGH_RISK_STATE_TRANSITION_PROXY`).

### 2. Deterministic Rule-Based & Baseline Models
- **Physics Rule Baseline:** Evaluated the deterministic physics momentum engine (`baseline_risk`) as a benchmark.
- **Logistic Regression Baseline:** Implemented standard linear baseline with balanced class weights.
- **Random Forest Baseline:** Implemented tree ensemble baseline (`n_estimators=100`, `max_depth=6`).

### 3. Primary XGBoost Early-Warning Classifier
- **Architecture:** `xgboost.XGBClassifier` with `scale_pos_weight` to address target class imbalance.
- **Validation Threshold Selection:** Optimal operating threshold selected strictly on the **Validation Split** by maximizing $F1$-score ($0.10 - 0.90$ search grid).
- **Probability Calibration:** Applied Platt Scaling (Logistic Regression on validation probabilities) to ensure predicted probabilities match empirical risk probabilities and minimize Brier score.

### 4. Comprehensive Evaluation & Explainability
- **Metrics Computed:** Accuracy, Precision, Recall, $F1$-score, ROC-AUC, PR-AUC, Confusion Matrix ($TN, FP, FN, TP$), False Positive Rate ($FPR$), False Negative Rate ($FNR$), and Brier Score Loss.
- **Early Warning Lead Time:** Evaluated proxy early-warning lead time in seconds prior to risk state transition.
- **Explainability Engine:** Integrated local/global feature attributions using SHAP / Tree-Explainer attributions to explain individual predictions to field operators.

### 5. Versioned Model Registry
- **Artifact Package Directory:** `models/risk/<version>/` containing:
  - `model.json` / `model.pkl` (Model binary)
  - `metadata.json` (Provenance, hyperparams, training duration, honesty tags)
  - `feature_schema.json` (Canonical input feature list)
  - `evaluation.json` (Test metrics breakdown)
  - `calibration.pkl` (Probability calibrator artifact)
  - `threshold.json` (Operating decision threshold)
- **Active Version Pointer:** Managed via `models/risk/active_version.txt`.

---

## Model Benchmarking & Performance Comparison

| Model Name | Precision | Recall | F1-Score | ROC-AUC | PR-AUC | Brier Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Rule-Based Physics Baseline** | 0.0000 | 0.0000 | 0.0000 | 0.9875 | 0.9819 | 0.1275 |
| **Logistic Regression Baseline** | 0.9778 | 1.0000 | 0.9888 | 0.9891 | 0.9889 | 0.0111 |
| **Random Forest Baseline** | 0.9778 | 1.0000 | 0.9888 | 0.9891 | 0.9889 | 0.0095 |
| **XGBoost Early-Warning Classifier** | **0.9778** | **1.0000** | **0.9888** | **0.9891** | **0.9889** | **0.0136** |

---

## Critical Honesty & Transparency Declaration

> [!IMPORTANT]
> **PROTOTYPE / PROXY LABEL LIMITATION NOTICE**
> 1. **Proxy Ground Truth:** All training targets in Phase 4 are derived from physics-based state transitions (`HIGH_RISK_STATE_TRANSITION_PROXY` or physics momentum thresholds), **NOT** from validated real-world stampede incidents.
> 2. **Model Status Tag:** All models in the registry are explicitly assigned `model_status = "PROTOTYPE"` and `ground_truth_status = "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED"`.
> 3. **Operational Boundary:** Prototype AI predictions do **NOT** replace the deterministic physics baseline engine (`current_risk`). The operator API provides both values clearly separated:
>    - `current_risk`: Deterministic physics baseline calculation.
>    - `ai_model_prediction`: Statistical probability of future risk state escalation.

---

## CLI Tools & Execution Commands

### Train, Tune, Calibrate, & Register Model
```bash
python scripts/train_risk_model.py --dataset data/dataset_v1 --target HIGH_RISK_WITHIN_5M --source MIXED_EXPLICIT
```

### Evaluate Registered Prototype Model
```bash
python scripts/evaluate_risk_model.py --dataset data/dataset_v1
```

### Run Test Suite
```bash
python -m pytest tests/
```
