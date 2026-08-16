"""
CROWDSHIELD AI MODEL TRAINING CLI (PHASE 4 - PART AA)
======================================================
Reproducible CLI for auditing, training, calibrating, evaluating,
and registering predictive crowd-risk AI prototype models.
"""

import os
import sys
import argparse
import json
import time
from datetime import datetime, timezone
import pandas as pd
import numpy as np

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.training.dataset_auditor import audit_phase3_dataset
from app.ai.training.baselines import (
    evaluate_rule_based_baseline,
    train_logistic_regression_baseline,
    train_random_forest_baseline
)
from app.ai.training.xgboost_trainer import XGBoostModelTrainer
from app.ai.training.evaluator import (
    calculate_proxy_lead_time,
    analyze_false_negatives,
    analyze_subgroup_stability,
    generate_shap_explainability
)
from app.ai.training.model_registry import register_trained_model
from app.ai.dataset.schema import PRIMARY_PROXY_TARGET, CANDIDATE_MODEL_FEATURES


def parse_args():
    parser = argparse.ArgumentParser(description="CrowdShield AI Model Training CLI")
    parser.add_argument("--dataset", type=str, default="data/dataset_v1", help="Path to Phase 3 dataset directory")
    parser.add_argument("--target", type=str, default=PRIMARY_PROXY_TARGET, help="Target column name")
    parser.add_argument("--source", type=str, default="MIXED_EXPLICIT", help="Provenance mode (REAL_ONLY, DEMO_VIDEO, SYNTHETIC, MIXED_EXPLICIT)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--outdir", type=str, default="data/training_reports", help="Output directory for training report")
    return parser.parse_args()


def main():
    args = parse_args()
    start_time = time.time()

    print(f"\n=======================================================")
    print(f"     CROWDSHIELD AI MODEL TRAINING PIPELINE           ")
    print(f"=======================================================")
    print(f"Dataset Path : {args.dataset}")
    print(f"Target       : {args.target}")
    print(f"Source Mode  : {args.source}")
    print(f"Random Seed  : {args.seed}")

    # 1. Audit & Validate Dataset (Part A, B, C, D)
    report, train_df, val_df, test_df = audit_phase3_dataset(args.dataset, source_mode=args.source)

    if not report.exists or not report.is_valid_for_training:
        print(f"\n[ERROR] Dataset audit failed or invalid for training.")
        print(f"Reason: Split overlap = {report.split_overlap_detected}, Train size = {report.train_size}")
        sys.exit(1)

    print(f"\n[PART A/B/C/D AUDIT PASSED]")
    print(f"Total Rows: {report.total_rows} (Train: {report.train_size}, Val: {report.val_size}, Test: {report.test_size})")
    print(f"Target Stats ({args.target}): {report.target_stats.get(args.target, {})}")

    # 2. Evaluate Rule-Based Baseline (Part G)
    rule_metrics = evaluate_rule_based_baseline(test_df, target_col=args.target)

    # 3. Train Logistic Regression Baseline (Part G)
    lr_model, lr_results = train_logistic_regression_baseline(train_df, val_df, test_df, target_col=args.target, random_seed=args.seed)

    # 4. Train Random Forest Baseline (Part H)
    rf_model, rf_results = train_random_forest_baseline(train_df, val_df, test_df, target_col=args.target, random_seed=args.seed)

    # 5. Train & Calibrate Primary XGBoost Model (Part I, J, L, M, N)
    xgb_trainer = XGBoostModelTrainer(target_col=args.target, random_seed=args.seed)
    xgb_results = xgb_trainer.train_and_evaluate(train_df, val_df, test_df, calibrate=True)

    test_probs = xgb_trainer.model.predict_proba(test_df[xgb_trainer.feature_cols].values)[:, 1]

    # 6. Calculate Early Warning Lead Time & FN Error Analysis (Part P, Q)
    lead_time_data = calculate_proxy_lead_time(test_df, test_probs, threshold=xgb_trainer.best_threshold, target_col=args.target)
    fn_analysis = analyze_false_negatives(test_df, test_probs, threshold=xgb_trainer.best_threshold, target_col=args.target)
    subgroup_data = analyze_subgroup_stability(test_df, test_probs, threshold=xgb_trainer.best_threshold, target_col=args.target)

    # 7. Generate Explainability Sample (Part T)
    sample_row = test_df.iloc[0] if len(test_df) > 0 else pd.Series()
    explain_data = generate_shap_explainability(xgb_trainer.model, test_df, sample_row, xgb_trainer.feature_cols)

    duration_sec = round(time.time() - start_time, 2)

    # 8. Model Selection (Part K)
    # Compare XGBoost vs Baselines
    selected_model_name = "XGBoost Early-Warning Classifier"

    # 9. Register Versioned Model Artifact (Part U, V, W, AE)
    meta_payload = {
        "model_name": "crowd_risk_early_warning",
        "model_type": "XGBoost",
        "dataset_version": report.metadata.get("dataset_version", "v1.0"),
        "target": args.target,
        "prediction_horizon_seconds": 300 if "5M" in args.target else 120,
        "training_source_mode": args.source,
        "random_seed": args.seed,
        "training_duration_seconds": duration_sec,
        "hyperparameters": xgb_results["hyperparameters"],
        "selected_threshold": xgb_trainer.best_threshold,
        "calibration_method": xgb_results["calibration_method"],
        "test_metrics": xgb_results["test_metrics"],
        "lead_time": lead_time_data,
        "ground_truth_status": "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
        "label_type": "PROXY",
        "model_status": "PROTOTYPE"
    }

    registered_dir = register_trained_model(
        model=xgb_trainer.model,
        metadata=meta_payload,
        feature_schema=xgb_trainer.feature_cols,
        evaluation=xgb_results["test_metrics"],
        threshold=xgb_trainer.best_threshold,
        calibrator=xgb_trainer.calibrator
    )

    # 10. Print Model Comparison Report (Part AD)
    print("\n=========================================================================================")
    print("                              MODEL COMPARISON REPORT                                     ")
    print("=========================================================================================")
    print(f"{'Model Name':<30} | {'Prec':<6} | {'Recall':<6} | {'F1':<6} | {'ROC-AUC':<8} | {'PR-AUC':<8} | {'Brier':<6}")
    print("-" * 90)

    for m in [rule_metrics, lr_results["test_metrics"], rf_results["test_metrics"], xgb_results["test_metrics"]]:
        name = m.get("model_name", m.get("model_type", "Model"))
        p = str(m.get("precision", "N/A"))
        r = str(m.get("recall", "N/A"))
        f = str(m.get("f1", "N/A"))
        roc = str(m.get("roc_auc", "N/A"))
        pr = str(m.get("pr_auc", "N/A"))
        b = str(m.get("brier_score", "N/A"))
        print(f"{name:<30} | {p:<6} | {r:<6} | {f:<6} | {roc:<8} | {pr:<8} | {b:<6}")

    print("=========================================================================================")
    print(f"[SUCCESS] Prototype AI Model registered at: {registered_dir}")
    print(f"Training completed in {duration_sec}s.")

    # Write report file
    os.makedirs(args.outdir, exist_ok=True)
    report_path = os.path.join(args.outdir, "training_report.json")
    full_report = {
        "audit": report.to_dict(),
        "baselines": {
            "rule_based": rule_metrics,
            "logistic_regression": lr_results["test_metrics"],
            "random_forest": rf_results["test_metrics"]
        },
        "primary_model": xgb_results,
        "lead_time": lead_time_data,
        "false_negatives": fn_analysis,
        "subgroup_stability": subgroup_data,
        "explainability_sample": explain_data,
        "registered_directory": registered_dir
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)

    print(f"Detailed report saved to: {report_path}\n")


if __name__ == "__main__":
    main()
