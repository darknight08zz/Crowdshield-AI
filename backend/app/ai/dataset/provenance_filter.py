"""
CROWDSHIELD TELEMETRY PROVENANCE FILTER
=======================================
Enforces explicit separation between REAL, DEMO_VIDEO, SYNTHETIC, and SIMULATED telemetry.
"""

from typing import List, Dict, Any
import pandas as pd


VALID_DATASET_MODES = ["REAL_ONLY", "DEMO_VIDEO", "SYNTHETIC", "MIXED_EXPLICIT"]


def filter_telemetry_by_provenance(
    df: pd.DataFrame,
    source_mode: str = "MIXED_EXPLICIT"
) -> pd.DataFrame:
    """
    Filters input telemetry DataFrame according to strict provenance criteria.

    Args:
        df (pd.DataFrame): Raw or normalized telemetry DataFrame.
        source_mode (str): One of ["REAL_ONLY", "DEMO_VIDEO", "SYNTHETIC", "MIXED_EXPLICIT"].

    Returns:
        pd.DataFrame: Filtered DataFrame matching requested provenance rules.
    """
    if source_mode not in VALID_DATASET_MODES:
        raise ValueError(f"Invalid dataset source mode '{source_mode}'. Must be one of {VALID_DATASET_MODES}")

    if df.empty:
        return df

    filtered_df = df.copy()

    # Normalize default provenance columns if missing
    if "is_synthetic" not in filtered_df.columns:
        filtered_df["is_synthetic"] = False
    if "is_simulated" not in filtered_df.columns:
        filtered_df["is_simulated"] = False
    if "is_degraded" not in filtered_df.columns:
        filtered_df["is_degraded"] = False
    if "processing_mode" not in filtered_df.columns:
        filtered_df["processing_mode"] = "LIVE"

    if source_mode == "REAL_ONLY":
        filtered_df = filtered_df[
            (~filtered_df["is_synthetic"]) &
            (~filtered_df["is_simulated"]) &
            (filtered_df["processing_mode"] == "LIVE")
        ]
    elif source_mode == "DEMO_VIDEO":
        filtered_df = filtered_df[
            (~filtered_df["is_synthetic"]) &
            (filtered_df["processing_mode"] == "DEMO")
        ]
    elif source_mode == "SYNTHETIC":
        filtered_df = filtered_df[
            (filtered_df["is_synthetic"]) | (filtered_df["is_simulated"])
        ]
    elif source_mode == "MIXED_EXPLICIT":
        # Keep all records intact, maintaining explicit provenance labels
        pass

    return filtered_df.reset_index(drop=True)
