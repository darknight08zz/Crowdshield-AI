"""
CROWDSHIELD SCALER PREPARATION & NORMALIZATION PIPELINE
======================================================
Prepares scaling parameters strictly fitted on the TRAINING split dataframe to prevent data leakage.
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np

from app.ai.dataset.schema import CANDIDATE_MODEL_FEATURES


def compute_training_scaler_params(
    train_df: pd.DataFrame,
    features: List[str] = CANDIDATE_MODEL_FEATURES
) -> Dict[str, Dict[str, float]]:
    """
    Computes mean, std, min, and max scaling statistics ONLY from the training dataset split.

    STRICT GUARANTEE:
    Scaling parameters must NOT be computed over the validation or test splits.

    Returns:
        Dict[str, Dict[str, float]]: {
            "density": {"mean": float, "std": float, "min": float, "max": float},
            ...
        }
    """
    scaler_params = {}

    for feat in features:
        if feat in train_df.columns:
            vals = train_df[feat].dropna().values
            if len(vals) > 0:
                mean_val = float(np.mean(vals))
                std_val = float(np.std(vals))
                min_val = float(np.min(vals))
                max_val = float(np.max(vals))
            else:
                mean_val, std_val, min_val, max_val = 0.0, 1.0, 0.0, 1.0

            scaler_params[feat] = {
                "mean": round(mean_val, 6),
                "std": round(std_val if std_val > 1e-6 else 1.0, 6),
                "min": round(min_val, 6),
                "max": round(max_val, 6),
            }

    return scaler_params
