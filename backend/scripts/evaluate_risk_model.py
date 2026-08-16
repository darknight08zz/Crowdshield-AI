"""
CROWDSHIELD MODEL EVALUATION CLI (PHASE 4 - PART AB)
=====================================================
Evaluates a registered versioned risk model against a target dataset,
generating an evaluation report, confusion matrix metrics, and explainability attributions.
"""

import os
import sys
import argparse
import json
import pandas as pd
import numpy as np

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.model_loader import load_registered_model, predict_risk_probability
from app.ai.training.baselines import evaluate_metrics
from app.ai.training.evaluator import (
    calculate_proxy_lead_time,
    analyze_false_negatives,
    analyze_subgroup_stability,
    generate_shap_explainability
)


def parse_args():
    parser = argparse.ArgumentParser(description="CrowdShield Model Evaluation CLI")
    parser.add_argument("--dataset", type=str, default="data/dataset_v1", help="Path to Phase 3 dataset directory")
    parser.add_argument("--version_dir", type=str, default=None, help="Path to versioned model directory (defaults to active model)")
    parser.add_argument("--outdir", type=str, default="data/evaluation_reports", help="Output directory for evaluation report")
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"\n=======================================================")
    print(f"       CROWDSHIELD AI MODEL EVALUATION CLI             ")
    print(f"=======================================================")

    model_data = load_registered_model(args.version_dir)
    if not model_data or not model_data.get("model"):
        print("[ERROR] No registered prototype model found to evaluate.")
        sys.exit(1)

    metadata = model_data["metadata"]
    target_col = metadata.get("target", "HIGH_RISK_WITHIN_5M")
    threshold = model_data["threshold"]
    feature_cols = model_data["feature_cols"]

    print(f"Model Version : {metadata.get('model_version', 'Unknown')}")
    print(f"Model Status  : {metadata.get('model_status', 'PROTOTYPE')}")
    print(f"Target Column : {target_col}")
    print(f"Threshold     : {threshold}")

    test_path = os.path.join(args.dataset, "test_dataset.csv")
    if not os.path.exists(test_path):
        print(f"[ERROR] Test dataset split not found at: {test_path}")
        sys.exit(1)

    test_df = pd.read_csv(test_path)
    if target_col not in test_df.columns:
        print(f"[ERROR] Target column '{target_col}' not in test dataset.")
        sys.exit(1)

    probs = []
    for _, row in test_df.iterrows():
        feat_dict = {col: float(row[col]) for col in feature_cols if col in test_df.columns}
        res = predict_risk_probability(feat_dict)
        probs.append(res.get("probability_high_risk", 0.0))

    y_prob = np.array(probs)
    y_true = test_df[target_col].values.astype(int)

    metrics = evaluate_metrics(y_true, y_prob, threshold=threshold)
    lead_time = calculate_proxy_lead_time(test_df, y_prob, threshold=threshold, target_col=target_col)
    fn_analysis = analyze_false_negatives(test_df, y_prob, threshold=threshold, target_col=target_col)
    subgroup = analyze_subgroup_stability(test_df, y_prob, threshold=threshold, target_col=target_col)

    sample_explain = generate_shap_explainability(model_data["model"], test_df, test_df.iloc[0], feature_cols)

    eval_report = {
        "model_version": metadata.get("model_version"),
        "model_status": metadata.get("model_status"),
        "target": target_col,
        "selected_threshold": threshold,
        "test_metrics": metrics,
        "lead_time": lead_time,
        "false_negatives": fn_analysis,
        "subgroup_stability": subgroup,
        "explainability_sample": sample_explain
    }

    os.makedirs(args.outdir, exist_ok=True)
    out_path = os.path.join(args.outdir, f"evaluation_{metadata.get('model_version', 'v1')}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(eval_report, f, indent=2)

    print("\n[EVALUATION METRICS]")
    print(f"Accuracy  : {metrics['accuracy']}")
    print(f"Precision : {metrics['precision']}")
    print(f"Recall    : {metrics['recall']}")
    print(f"F1-Score  : {metrics['f1']}")
    print(f"ROC-AUC   : {metrics['roc_auc']}")
    print(f"PR-AUC    : {metrics['pr_auc']}")
    print(f"Brier     : {metrics['brier_score']}")
    print(f"\n[REPORT SAVED] Evaluation saved to: {out_path}\n")


if __name__ == "__main__":
    main()
