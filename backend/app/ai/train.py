"""
CROWDSHIELD MODEL TRAINING SCRIPT
=================================
Generates synthetic crowd physics training data based on crowd dynamics principles,
trains an XGBoost regressor model, and serializes the model artifact to disk.

REPLACEMENT NOTICE FOR PRODUCTION DEPLOYMENT:
---------------------------------------------
When real event sensor logs and incident datasets become available, replace
`generate_synthetic_training_data()` with a loader reading historical telemetry from your
PostgreSQL / data warehouse, then re-run `python -m app.ai.train`.
"""

import os
import sys
from typing import Tuple
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

# Add backend directory to sys.path for standalone script execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.ai.features import FEATURE_NAMES

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
MODEL_FILE_PATH = os.path.join(MODEL_DIR, "xgboost_risk_model.json")


def generate_synthetic_training_data(num_samples: int = 5000) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Encodes physical crowd safety domain rules to produce realistic training data:
    - Density > 0.70 + Speed < 0.5 m/s + Inflow > Outflow = High Stampede Risk (> 75/100)
    - Low density (< 0.40) + Speed > 1.0 m/s = Safe (< 25/100)
    - 5-minute future risk projects trajectory based on current inflow/outflow delta.
    """
    np.random.seed(42)

    # 1. Feature sampling
    density = np.random.uniform(0.1, 0.98, num_samples)
    inflow = np.random.uniform(20.0, 250.0, num_samples)
    outflow = np.random.uniform(20.0, 250.0, num_samples)
    speed = np.clip(1.50 - (density * 1.3) + np.random.normal(0, 0.1, num_samples), 0.15, 1.8)
    conflict = np.clip(0.10 + (density * 0.6) + np.random.normal(0, 0.08, num_samples), 0.0, 1.0)
    gate_util = np.clip((inflow / 180.0) + np.random.normal(0, 0.05, num_samples), 0.0, 1.0)
    incidents = np.random.choice([0, 1, 2, 3], size=num_samples, p=[0.85, 0.10, 0.04, 0.01])
    reverse_flow = np.clip(0.05 + (density * 0.5) + np.random.normal(0, 0.08, num_samples), 0.0, 1.0)
    blockage = np.clip(0.08 + (density * 0.55) + np.random.normal(0, 0.08, num_samples), 0.0, 1.0)

    # 2. Physics-informed ground truth formulas
    # Net flow accumulation ratio
    flow_delta_ratio = np.clip((inflow - outflow) / np.maximum(outflow, 30.0), -1.0, 2.0)
    
    # Base risk score calculation (0 to 100)
    base_risk = (
        (density ** 2) * 40.0 +                     # Non-linear density weight (up to 40 pts)
        np.maximum(0, 1.0 - speed) * 15.0 +        # Slow movement penalty (up to 15 pts)
        np.maximum(0, flow_delta_ratio) * 15.0 +   # Net compression accumulation (up to 15 pts)
        conflict * 10.0 +                          # Turbulence penalty (up to 10 pts)
        incidents * 5.0 +                          # Active incident penalty (up to 10 pts)
        reverse_flow * 10.0 +                      # Reverse flow penalty (up to 10 pts)
        blockage * 10.0                            # Spatially-concentrated blockage penalty (up to 10 pts)
    )
    current_risk = np.clip(base_risk + np.random.normal(0, 2.0, num_samples), 0.0, 100.0)

    # 5-minute risk trajectory projection (accounts for accumulation velocity)
    future_risk = np.clip(
        current_risk + (flow_delta_ratio * 12.0) + (incidents * 3.0) + np.random.normal(0, 2.0, num_samples),
        0.0, 100.0
    )

    X = pd.DataFrame({
        "current_density": density,
        "inflow_rate": inflow,
        "outflow_rate": outflow,
        "avg_pedestrian_speed": speed,
        "direction_conflict_score": conflict,
        "gate_capacity_utilization": gate_util,
        "recent_incident_count_10min": incidents,
        "reverse_flow_ratio": reverse_flow,
        "blockage_score": blockage
    })[FEATURE_NAMES]

    y_current = pd.Series(current_risk, name="current_risk_score")
    y_future = pd.Series(future_risk, name="predicted_risk_5min")

    return X, y_current, y_future


def train_and_save_model():
    """
    Trains the XGBoost Regressor model on crowd risk features and serializes the model.
    """
    os.makedirs(MODEL_DIR, exist_ok=True)
    print("[+] Generating synthetic physical training dataset (5,000 samples)...")
    X, y_current, y_future = generate_synthetic_training_data(num_samples=5000)

    X_train, X_test, y_train, y_test = train_test_split(X, y_current, random_state=42, test_size=0.2)

    print("[+] Training XGBoost Regressor model...")
    model = xgb.XGBRegressor(
        n_estimators=120,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42
    )

    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mse = mean_squared_error(y_test, preds)
    r2 = r2_score(y_test, preds)

    print(f"[SUCCESS] Model trained. Test MSE: {mse:.4f} | R² Score: {r2:.4f}")

    # Save model artifact
    model.save_model(MODEL_FILE_PATH)
    print(f"[SUCCESS] Model serialized to {MODEL_FILE_PATH}")


if __name__ == "__main__":
    train_and_save_model()
