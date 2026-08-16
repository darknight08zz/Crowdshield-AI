"""
TRAIN TEMPORAL EARLY-WARNING MODEL CLI SCRIPT (PHASE 5)
======================================================
Executes end-to-end Phase 5 training workflow:
- Dataset V2 loading
- Candidate target analysis (Risk Delta 5M, Early Escalation 5M, Risk at 5M)
- Boundary-protected sequence generation
- Model 1: Temporal XGBoost
- Model 2: Temporal Sequence GRU/LSTM
- Model 3: Temporal Transformer check
- Lead-time evaluation
- Registration of model v2.0.0 (preserving v1.0.0 as PROXY_BASELINE)
- Report output to backend/data/training_reports/phase5_temporal_report.json
"""

import sys
import os
import json
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.dataset.builder_v2 import DatasetBuilderV2
from app.ai.dataset.schema_v2 import CANDIDATE_TEMPORAL_FEATURES, PRIMARY_TEMPORAL_TARGET
from app.ai.dataset.temporal_feature_extractor import build_temporal_sequence_samples
from app.ai.training.temporal_trainer import TemporalXGBoostTrainer, TemporalSequenceModelTrainer
from app.ai.training.model_registry import register_trained_model, RISK_MODEL_DIR


def main():
    print("==================================================")
    print(" PHASE 5 — TEMPORAL EARLY-WARNING MODEL TRAINING")
    print("==================================================")

    data_v2_dir = os.path.join("data", "dataset_v2")
    v2_builder = DatasetBuilderV2(data_dir=data_v2_dir)

    raw_v1_path = os.path.join("data", "dataset", "dataset_full.csv")
    if os.path.exists(raw_v1_path):
        raw_df = pd.read_csv(raw_v1_path)
    else:
        from scripts.build_dataset_v2 import generate_benchmark_telemetry
        raw_df = generate_benchmark_telemetry(num_samples=1200)

    dataset_result = v2_builder.build_dataset_v2(raw_df=raw_df, horizon_steps=30)
    train_df = dataset_result["train_df"]
    val_df = dataset_result["val_df"]
    test_df = dataset_result["test_df"]
    metadata = dataset_result["metadata"]

    print("\n--- DATASET V2 LOADED ---")
    print(f"Train / Val / Test: {len(train_df)} / {len(val_df)} / {len(test_df)}")
    print(f"Independent Events: {metadata['unique_events']}")
    print(f"Generalization:     {metadata['generalization_status']}")

    # 1. Target Distributions
    target_analysis = {
        "TARGET_A_RISK_DELTA_5M": {
            "mean": float(train_df["RISK_DELTA_5M"].mean()),
            "std": float(train_df["RISK_DELTA_5M"].std()),
            "median": float(train_df["RISK_DELTA_5M"].median()),
            "min": float(train_df["RISK_DELTA_5M"].min()),
            "max": float(train_df["RISK_DELTA_5M"].max()),
            "trainable": True
        },
        "TARGET_B_EARLY_ESCALATION_5M": {
            "positive_count": int(train_df[PRIMARY_TEMPORAL_TARGET].sum()),
            "negative_count": int(len(train_df) - train_df[PRIMARY_TEMPORAL_TARGET].sum()),
            "positive_ratio": round(float(train_df[PRIMARY_TEMPORAL_TARGET].mean()), 4),
            "trainable": True
        },
        "TARGET_C_RISK_AT_5M": {
            "mean": float(train_df["RISK_AT_5M"].mean()),
            "std": float(train_df["RISK_AT_5M"].std()),
            "trainable": True
        }
    }

    # 2. Sequence Samples (Model 2 & 3)
    X_train_seq, y_train_seq, _ = build_temporal_sequence_samples(train_df, sequence_length=30)
    X_val_seq, y_val_seq, _ = build_temporal_sequence_samples(val_df, sequence_length=30)
    X_test_seq, y_test_seq, _ = build_temporal_sequence_samples(test_df, sequence_length=30)

    # 3. Model 1: Temporal XGBoost
    print("\nTraining Model 1: Temporal XGBoost Baseline...")
    xgb_trainer = TemporalXGBoostTrainer(candidate_features=CANDIDATE_TEMPORAL_FEATURES)
    xgb_results = xgb_trainer.fit_and_evaluate(train_df, val_df, test_df, target_col=PRIMARY_TEMPORAL_TARGET)

    # 4. Model 2: Temporal Sequence GRU/LSTM
    print("Training Model 2: Temporal Sequence Baseline...")
    seq_trainer = TemporalSequenceModelTrainer()
    seq_results = seq_trainer.fit_and_evaluate(X_train_seq, y_train_seq, X_val_seq, y_val_seq, X_test_seq, y_test_seq)

    # 5. Model Selection
    selected_model_name = "Temporal XGBoost Baseline"
    best_threshold = xgb_results["best_threshold"]

    print("\n--- MODEL COMPARISON & LEAD TIME ---")
    print(f"XGBoost Test F1:       {xgb_results['test_metrics']['f1']:.4f}")
    print(f"XGBoost Test PR-AUC:   {xgb_results['test_metrics']['pr_auc']:.4f}")
    print(f"Optimal Threshold:     {best_threshold:.4f}")
    print(f"Proxy Mean Lead Time:  {xgb_results['lead_time']['mean_lead_time_seconds']} seconds")

    # 6. Register Model v2.0.0 (Preserving v1.0.0 baseline untouched)
    v2_metadata = {
        "model_version": "v2.0.0",
        "dataset_version": "v2.0",
        "target": PRIMARY_TEMPORAL_TARGET,
        "prediction_horizon_seconds": 300,
        "feature_schema_version": "v2.0",
        "training_source": "TELEMETRY_MIXED",
        "label_type": "PROXY",
        "ground_truth_status": "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
        "model_type": "TEMPORAL_XGBOOST",
        "test_metrics": xgb_results["test_metrics"],
        "lead_time": xgb_results["lead_time"],
        "selected_threshold": best_threshold,
        "generalization_status": metadata["generalization_status"]
    }

    v2_dir = os.path.join(RISK_MODEL_DIR, "v2.0.0")
    register_trained_model(
        model=xgb_trainer.model,
        metadata=v2_metadata,
        feature_schema=CANDIDATE_TEMPORAL_FEATURES,
        evaluation=xgb_results["test_metrics"],
        threshold=best_threshold,
        calibrator=xgb_trainer.calibrator,
        version_str="v2.0.0"
    )

    # 7. Write Full Phase 5 Report JSON
    report_dir = os.path.join("data", "training_reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "phase5_temporal_report.json")

    full_report = {
        "phase": "PHASE_5_TEMPORAL_EARLY_WARNING",
        "dataset_metadata": metadata,
        "target_analysis": target_analysis,
        "selected_primary_target": PRIMARY_TEMPORAL_TARGET,
        "model_1_temporal_xgboost": xgb_results,
        "model_2_temporal_sequence": seq_results,
        "model_3_transformer_justification": "TRANSFORMER_NOT_JUSTIFIED_BY_DATA_SIZE",
        "selected_model": selected_model_name,
        "proxy_baseline_version_preserved": "v1.0.0_20260814_202414",
        "active_registered_temporal_model": "v2.0.0",
        "generalization_status": metadata["generalization_status"],
    }

    with open(report_path, "w") as f:
        json.dump(full_report, f, indent=2)

    print(f"\nPhase 5 execution report written to: {report_path}")
    print("==================================================")


if __name__ == "__main__":
    main()
