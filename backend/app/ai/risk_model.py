"""
CROWDSHIELD RISK INFERENCE ENGINE
=================================
Loads the trained XGBoost model and provides fast real-time risk predictions
(current risk and 5-minute projected risk) from a feature vector.
"""

import os
from typing import Dict, Tuple
import pandas as pd
import xgboost as xgb

from app.ai.features import FEATURE_NAMES, SAFE_BASELINES

from app.ai.training.registry import get_active_model_path

_cached_model = None
_cached_model_path = None


def get_model() -> xgb.XGBRegressor:
    """
    Lazy-loads and caches the active serialized XGBoost regressor model from the registry.
    Auto-trains if model artifact is missing.
    """
    global _cached_model, _cached_model_path
    active_path = get_active_model_path()

    if _cached_model is None or _cached_model_path != active_path:
        if not os.path.exists(active_path):
            from app.ai.training.train import run_training_pipeline
            run_training_pipeline()
            active_path = get_active_model_path()

        model = xgb.XGBRegressor()
        model.load_model(active_path)
        _cached_model = model
        _cached_model_path = active_path

    return _cached_model


def predict_risk(feature_dict: Dict[str, float]) -> Dict[str, float]:
    """
    Evaluates multi-horizon risk predictions: current_risk, risk_2min, risk_5min, risk_10min.
    Uses Approach (b): Unified physics-guided momentum trajectory function parameterized by time horizon.

    Returns:
        Dict[str, float]: {
            "current_risk": float,
            "risk_2min": float,
            "risk_5min": float,
            "risk_10min": float
        }
    """
    model = get_model()

    # Format input row dataframe matching exact feature schema with fallback defaults
    full_feats = {**SAFE_BASELINES, **feature_dict}
    input_df = pd.DataFrame([full_feats])[FEATURE_NAMES]
    current_risk = float(model.predict(input_df)[0])
    current_risk = float(max(0.0, min(100.0, current_risk)))

    # Compute trajectory momentum delta from inflow/outflow balance and incident pressure
    inflow = feature_dict.get("inflow_rate", 80.0)
    outflow = feature_dict.get("outflow_rate", 80.0)
    incidents = feature_dict.get("recent_incident_count_10min", 0.0)

    flow_delta_ratio = (inflow - outflow) / max(outflow, 30.0)
    base_momentum_5min = (flow_delta_ratio * 10.0) + (incidents * 4.0)

    # Multi-horizon trajectory projections
    risk_2min = max(0.0, min(100.0, current_risk + (base_momentum_5min * 0.40)))
    risk_5min = max(0.0, min(100.0, current_risk + base_momentum_5min))
    # 10-minute projection incorporates saturation decay to avoid unrealistically diverging values
    risk_10min = max(0.0, min(100.0, current_risk + (base_momentum_5min * 1.75)))

    return {
        "current_risk": round(current_risk, 1),
        "risk_2min": round(risk_2min, 1),
        "risk_5min": round(risk_5min, 1),
        "risk_10min": round(risk_10min, 1)
    }
