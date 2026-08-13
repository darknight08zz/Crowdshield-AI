"""
CROWDSHIELD RETRAINABLE MODEL TRAINING PIPELINE
===============================================
Trains XGBoost model on real historical logs / academic datasets with class-imbalance weighting.
Logs Precision, Recall, and F1 on dangerous precursor states, and registers timestamped artifacts.
"""

import os
import sys
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, precision_score, recall_score, f1_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.ai.features import FEATURE_NAMES
from app.ai.training.data_loader import load_historical_telemetry
from app.ai.training.label_strategy import apply_domain_labeling_and_weights
from app.ai.training.registry import save_versioned_model


def run_training_pipeline(csv_file_path: str = None) -> Tuple[xgb.XGBRegressor, Dict[str, Any]]:
    """
    Executes end-to-end model training, validation, and versioned registry serialization.
    """
    print("=" * 60)
    print("CROWDSHIELD MODEL TRAINING PIPELINE")
    print("=" * 60)

    # 1. Load Data
    X = load_historical_telemetry(csv_file_path=csv_file_path, num_samples=6000)

    # 2. Apply Domain Labeling and Class Imbalance Weighting
    labels_df, y_precursor, sample_weights = apply_domain_labeling_and_weights(X)
    y_current = labels_df["current_risk"] if isinstance(labels_df, pd.DataFrame) else labels_df

    # 3. Train / Test Split
    X_train, X_test, y_train, y_test, w_train, w_test, p_train, p_test = train_test_split(
        X, y_current, sample_weights, y_precursor, test_size=0.20, random_state=42
    )

    # 4. Train Model with Sample Weights
    print("[+] Fitting XGBoost Regressor with High-Risk Precursor Sample Weighting...")
    model = xgb.XGBRegressor(
        n_estimators=140,
        max_depth=5,
        learning_rate=0.07,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42
    )

    model.fit(X_train, y_train, sample_weight=w_train)

    # 5. Evaluate Performance
    preds = model.predict(X_test)
    preds_clipped = np.clip(preds, 0.0, 100.0)

    mse = float(mean_squared_error(y_test, preds_clipped))
    rmse = float(np.sqrt(mse))
    r2 = float(r2_score(y_test, preds_clipped))

    # Evaluate High-Risk Precursor Detection (Threshold >= 65.0)
    binary_preds = (preds_clipped >= 65.0).astype(int)
    binary_true = (y_test >= 65.0).astype(int)

    precision = float(precision_score(binary_true, binary_preds, zero_division=0))
    recall = float(recall_score(binary_true, binary_preds, zero_division=0))
    f1 = float(f1_score(binary_true, binary_preds, zero_division=0))

    metrics = {
        "mse": round(mse, 4),
        "rmse": round(rmse, 4),
        "r2_score": round(r2, 4),
        "high_risk_precision": round(precision, 4),
        "high_risk_recall": round(recall, 4),
        "high_risk_f1": round(f1, 4),
        "train_samples": len(X_train),
        "test_samples": len(X_test)
    }

    print("\n[+] EVALUATION METRICS:")
    print(f"    - Regression RMSE: {metrics['rmse']:.2f}")
    print(f"    - R² Score: {metrics['r2_score']:.4f}")
    print(f"    - High-Risk Precursor Precision: {metrics['high_risk_precision'] * 100:.1f}%")
    print(f"    - High-Risk Precursor RECALL:    {metrics['high_risk_recall'] * 100:.1f}%  <-- SAFETY CRITICAL")
    print(f"    - High-Risk Precursor F1-Score:  {metrics['high_risk_f1'] * 100:.1f}%\n")

    # 6. Save Versioned Artifact in Registry
    version_path = save_versioned_model(model, metrics)

    return model, metrics


if __name__ == "__main__":
    run_training_pipeline()
