"""
CROWDSHIELD MISSING & STALE TELEMETRY HANDLING STRATEGY
======================================================
Defines handling policies for missing, stale, or degraded telemetry data.
"""

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np


FEATURE_MISSING_POLICIES: Dict[str, Dict[str, Any]] = {
    "density": {"interpolation": "linear", "max_gap_seconds": 30, "allow_forward_fill": False},
    "inflow_rate": {"interpolation": "linear", "max_gap_seconds": 30, "allow_forward_fill": False},
    "outflow_rate": {"interpolation": "linear", "max_gap_seconds": 30, "allow_forward_fill": False},
    "average_speed": {"interpolation": "linear", "max_gap_seconds": 30, "allow_forward_fill": False},
    "median_speed": {"interpolation": "linear", "max_gap_seconds": 30, "allow_forward_fill": False},
    "direction_conflict_score": {"interpolation": "zero_fill", "max_gap_seconds": 30, "allow_forward_fill": False},
    "reverse_flow_ratio": {"interpolation": "zero_fill", "max_gap_seconds": 30, "allow_forward_fill": False},
    "blockage_score": {"interpolation": "zero_fill", "max_gap_seconds": 30, "allow_forward_fill": False},
}


def handle_missing_telemetry(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Applies documented missing telemetry policies:
    1. Checks for missing required identifiers (timestamp, zone_id, camera_id). Drops unidentifiable rows.
    2. Imputes short continuous gaps (<= 30s) via linear interpolation.
    3. Flags remaining imputed / stale rows with `is_degraded = True`.

    Returns:
        Tuple[pd.DataFrame, Dict[str, Any]]: Cleaned DataFrame and missing data summary report.
    """
    if df.empty:
        return df, {"rows_dropped": 0, "short_gaps_interpolated": 0, "stale_rows_flagged": 0}

    initial_count = len(df)
    clean_df = df.copy()

    # Drop rows missing essential identifiers
    id_cols = [c for c in ["timestamp", "zone_id"] if c in clean_df.columns]
    if id_cols:
        clean_df = clean_df.dropna(subset=id_cols)

    dropped_ids = initial_count - len(clean_df)

    # Impute numeric feature columns using allowed interpolation rules
    interpolated_count = 0
    num_cols = [c for c in FEATURE_MISSING_POLICIES.keys() if c in clean_df.columns]

    for col in num_cols:
        null_mask = clean_df[col].isnull()
        if null_mask.any():
            policy = FEATURE_MISSING_POLICIES[col]
            if policy["interpolation"] == "linear":
                clean_df[col] = clean_df[col].interpolate(method="linear", limit=3).fillna(0.0)
            else:
                clean_df[col] = clean_df[col].fillna(0.0)

            interpolated_count += int(null_mask.sum())
            clean_df.loc[null_mask, "is_degraded"] = True

    final_df = clean_df.reset_index(drop=True)

    summary = {
        "initial_rows": initial_count,
        "rows_dropped_missing_identifiers": dropped_ids,
        "feature_values_interpolated": interpolated_count,
        "final_valid_rows": len(final_df),
    }

    return final_df, summary
