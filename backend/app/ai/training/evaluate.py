"""
CROWDSHIELD MODEL EVALUATION & COMPARISON REPORT
================================================
Compares new real-data model predictions against baseline synthetic model predictions
on identical benchmark inputs to verify improvement before deployment.
"""

import os
import sys
from typing import Dict, Any
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error, r2_score, recall_score, precision_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.ai.features import FEATURE_NAMES
from app.ai.training.data_loader import load_historical_telemetry
from app.ai.training.label_strategy import apply_domain_labeling_and_weights
from app.ai.training.registry import get_active_model_path, LEGACY_DEFAULT_PATH


def generate_evaluation_comparison_report(csv_file_path: str = None) -> Dict[str, Any]:
    """
    Evaluates active model vs legacy model on benchmark dataset.
    """
    print("=" * 70)
    print("CROWDSHIELD MODEL COMPARISON & EVALUATION REPORT")
    print("=" * 70)

    # 1. Load Benchmark Test Set
    X = load_historical_telemetry(csv_file_path=csv_file_path, num_samples=2000)
    y_current, y_precursor, _ = apply_domain_labeling_and_weights(X)

    active_path = get_active_model_path()
    print(f"[+] Active Model Path: {active_path}")
    print(f"[+] Benchmark Test Samples: {len(X)}")

    # 2. Load Models
    active_model = xgb.XGBRegressor()
    active_model.load_model(active_path)

    legacy_model = None
    if os.path.exists(LEGACY_DEFAULT_PATH) and LEGACY_DEFAULT_PATH != active_path:
        legacy_model = xgb.XGBRegressor()
        legacy_model.load_model(LEGACY_DEFAULT_PATH)

    # 3. Compute Active Model Predictions
    preds_active = np.clip(active_model.predict(X[FEATURE_NAMES]), 0.0, 100.0)
    mse_active = mean_squared_error(y_current, preds_active)
    rmse_active = np.sqrt(mse_active)
    r2_active = r2_score(y_current, preds_active)

    bin_active = (preds_active >= 65.0).astype(int)
    bin_true = (y_current >= 65.0).astype(int)

    rec_active = recall_score(bin_true, bin_active, zero_division=0)
    prec_active = precision_score(bin_true, bin_active, zero_division=0)

    report = {
        "active_model": {
            "path": active_path,
            "rmse": round(float(rmse_active), 2),
            "r2_score": round(float(r2_active), 4),
            "precursor_recall": round(float(rec_active) * 100, 1),
            "precursor_precision": round(float(prec_active) * 100, 1)
        }
    }

    if legacy_model:
        preds_legacy = np.clip(legacy_model.predict(X[FEATURE_NAMES]), 0.0, 100.0)
        rmse_legacy = np.sqrt(mean_squared_error(y_current, preds_legacy))
        r2_legacy = r2_score(y_current, preds_legacy)
        bin_legacy = (preds_legacy >= 65.0).astype(int)

        rec_legacy = recall_score(bin_true, bin_legacy, zero_division=0)
        prec_legacy = precision_score(bin_true, bin_legacy, zero_division=0)

        report["legacy_model"] = {
            "path": LEGACY_DEFAULT_PATH,
            "rmse": round(float(rmse_legacy), 2),
            "r2_score": round(float(r2_legacy), 4),
            "precursor_recall": round(float(rec_legacy) * 100, 1),
            "precursor_precision": round(float(prec_legacy) * 100, 1)
        }
        report["recall_delta_percent"] = round(report["active_model"]["precursor_recall"] - report["legacy_model"]["precursor_recall"], 1)

    print("\n[+] MODEL PERFORMANCE SUMMARY:")
    print(f"    Active Model  -> RMSE: {report['active_model']['rmse']} | Precursor Recall: {report['active_model']['precursor_recall']}% | Precision: {report['active_model']['precursor_precision']}%")
    if legacy_model:
        print(f"    Legacy Model  -> RMSE: {report['legacy_model']['rmse']} | Precursor Recall: {report['legacy_model']['precursor_recall']}% | Precision: {report['legacy_model']['precursor_precision']}%")
        print(f"    Recall Delta  -> {report['recall_delta_percent']:+}% Improvement in Danger Precursor Detection")

    print("=" * 70)
    return report


if __name__ == "__main__":
    generate_evaluation_comparison_report()
