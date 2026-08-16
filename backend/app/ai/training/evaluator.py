"""
CROWDSHIELD MODEL EVALUATOR & EXPLAINABILITY ENGINE (PHASE 4 - PARTS O-T)
==========================================================================
Computes comprehensive evaluation metrics, early warning proxy lead times,
false-negative error breakdown, subgroup stability analysis, and SHAP/tree explainability.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False

from app.ai.dataset.schema import CANDIDATE_MODEL_FEATURES
from app.ai.training.baselines import evaluate_metrics


def calculate_proxy_lead_time(
    df: pd.DataFrame,
    y_prob: np.ndarray,
    threshold: float = 0.5,
    target_col: str = "HIGH_RISK_WITHIN_5M"
) -> Dict[str, Any]:
    """
    Calculates proxy early warning lead time in seconds between first prediction warning and target state transition.
    """
    if df.empty or "timestamp" not in df.columns or target_col not in df.columns:
        return {"proxy_lead_time_seconds": 0.0, "status": "INSUFFICIENT_TIMESTAMP_DATA"}

    df_copy = df.copy()
    df_copy["pred_warning"] = (y_prob >= threshold).astype(int)
    df_copy["ts_dt"] = pd.to_datetime(df_copy["timestamp"])
    df_copy = df_copy.sort_values("ts_dt")

    lead_times = []

    # Group by zone if available
    zones = df_copy["zone_id"].unique() if "zone_id" in df_copy.columns else ["default_zone"]

    for zone in zones:
        zone_df = df_copy[df_copy["zone_id"] == zone] if "zone_id" in df_copy.columns else df_copy
        first_warning_ts = None

        for _, row in zone_df.iterrows():
            if row["pred_warning"] == 1 and first_warning_ts is None:
                first_warning_ts = row["ts_dt"]

            if row[target_col] == 1 and first_warning_ts is not None:
                lead_sec = (row["ts_dt"] - first_warning_ts).total_seconds()
                if lead_sec >= 0:
                    lead_times.append(lead_sec)
                first_warning_ts = None  # Reset for next episode

    avg_lead = float(np.mean(lead_times)) if len(lead_times) > 0 else 0.0
    return {
        "proxy_lead_time_seconds": round(avg_lead, 2),
        "episodes_evaluated": len(lead_times),
        "status": "PROXY_LEAD_TIME_CALCULATED" if len(lead_times) > 0 else "NO_TRANSITION_EPISODES_FOUND",
        "notice": "PROXY LEAD TIME based on physics risk transitions, NOT validated real stampedes."
    }


def analyze_false_negatives(
    df: pd.DataFrame,
    y_prob: np.ndarray,
    threshold: float = 0.5,
    target_col: str = "HIGH_RISK_WITHIN_5M"
) -> Dict[str, Any]:
    """
    Analyzes feature patterns for False Negative predictions (missed risk escalations).
    """
    if df.empty or target_col not in df.columns:
        return {"fn_count": 0, "fn_analysis": "No data available."}

    y_true = df[target_col].values.astype(int)
    y_pred = (y_prob >= threshold).astype(int)

    fn_mask = (y_true == 1) & (y_pred == 0)
    fn_df = df[fn_mask]

    if fn_df.empty:
        return {"fn_count": 0, "summary": "Zero False Negatives detected on evaluation set."}

    fn_summary = {}
    for col in ["density", "average_speed", "inflow_rate", "direction_conflict_score", "blockage_score"]:
        if col in fn_df.columns:
            fn_summary[col] = {
                "fn_mean": round(float(fn_df[col].mean()), 4),
                "overall_mean": round(float(df[col].mean()), 4)
            }

    return {
        "fn_count": int(len(fn_df)),
        "fn_ratio": round(float(len(fn_df) / len(df)), 4),
        "feature_pattern_summary": fn_summary
    }


def analyze_subgroup_stability(
    df: pd.DataFrame,
    y_prob: np.ndarray,
    threshold: float = 0.5,
    target_col: str = "HIGH_RISK_WITHIN_5M"
) -> Dict[str, Any]:
    """
    Evaluates model performance metrics across zones, cameras, or events.
    """
    if df.empty or "zone_id" not in df.columns or target_col not in df.columns:
        return {"status": "NOT_ENOUGH_DATA_FOR_SUBGROUP_VALIDATION"}

    zone_results = {}
    for zone, group in df.groupby("zone_id"):
        if len(group) >= 5:
            idxs = group.index
            group_probs = y_prob[idxs] if len(y_prob) == len(df) else y_prob[:len(group)]
            group_y = group[target_col].values.astype(int)
            zone_results[str(zone)] = evaluate_metrics(group_y, group_probs, threshold=threshold)

    if not zone_results:
        return {"status": "NOT_ENOUGH_DATA_FOR_SUBGROUP_VALIDATION"}

    return {
        "status": "SUBGROUP_VALIDATED",
        "zone_breakdown": zone_results
    }


def generate_shap_explainability(
    model: Any,
    feature_df: pd.DataFrame,
    sample_row: pd.Series,
    feature_cols: List[str]
) -> Dict[str, Any]:
    """
    Generates local and global feature attribution explanations for a given prediction sample.
    Uses SHAP if available; falls back to feature contribution scoring otherwise.
    """
    feat_values = {col: float(sample_row[col]) for col in feature_cols if col in sample_row}
    row_input = pd.DataFrame([feat_values])[feature_cols]

    if HAS_SHAP:
        try:
            explainer = shap.Explainer(model, feature_df[feature_cols])
            shap_values = explainer(row_input)
            vals = shap_values.values[0]

            contributions = {}
            for col, val in zip(feature_cols, vals):
                contributions[col] = round(float(val), 4)

            sorted_contribs = dict(sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True))
            return {
                "method": "SHAP_TreeExplainer",
                "top_contributors": sorted_contribs,
                "notice": "Values represent feature attributions toward model risk prediction."
            }
        except Exception:
            pass

    # Fallback Feature Attribution
    importances = getattr(model, "feature_importances_", None)
    if importances is not None:
        contributions = {}
        for col, imp in zip(feature_cols, importances):
            val = feat_values.get(col, 0.0)
            contributions[col] = round(float(imp * val), 4)

        sorted_contribs = dict(sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True))
        return {
            "method": "Feature_Importance_Weighted_Contribution",
            "top_contributors": sorted_contribs,
            "notice": "Values represent feature contributions to model risk prediction."
        }

    return {
        "method": "UNAVAILABLE",
        "top_contributors": {},
        "notice": "Explainability engine unavailable for model type."
    }
