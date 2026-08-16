"""
CROWDSHIELD LEAKAGE-FREE DATASET SPLITTER
=========================================
Implements chronological and event-level dataset partitioning to prevent temporal and group leakage.

CRITICAL RULE:
--------------
DO NOT use random row-level train/test splitting for time-series telemetry.
Adjacent timestamps from the same event MUST NOT be split across train and test.
"""

from typing import Dict, Any, Tuple
import pandas as pd


def split_dataset_leakage_free(
    df: pd.DataFrame,
    strategy: str = "CHRONOLOGICAL",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    group_col: str = "event_id"
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Partitions dataset into train, validation, and test sets without data leakage.

    Strategies:
    1. CHRONOLOGICAL: Sorts by timestamp and cuts time intervals sequentially.
    2. EVENT_LEVEL: Group by `event_id` or `zone_id` ensuring whole events belong to single splits.

    Returns:
        Tuple[train_df, val_df, test_df, metadata_dict]
    """
    if df.empty:
        empty_df = pd.DataFrame()
        return empty_df, empty_df, empty_df, {"strategy": strategy, "total_rows": 0}

    total_rows = len(df)

    if strategy == "EVENT_LEVEL" and group_col in df.columns and df[group_col].nunique() > 1:
        unique_groups = df[group_col].dropna().unique()
        num_groups = len(unique_groups)

        train_count = int(max(1, num_groups * train_ratio))
        val_count = int(max(1, num_groups * val_ratio))

        train_groups = unique_groups[:train_count]
        val_groups = unique_groups[train_count : train_count + val_count]
        test_groups = unique_groups[train_count + val_count :]

        train_df = df[df[group_col].isin(train_groups)].reset_index(drop=True)
        val_df = df[df[group_col].isin(val_groups)].reset_index(drop=True)
        test_df = df[df[group_col].isin(test_groups)].reset_index(drop=True)

        meta = {
            "strategy": "EVENT_LEVEL",
            "group_column": group_col,
            "total_groups": num_groups,
            "train_groups": [str(g) for g in train_groups],
            "val_groups": [str(g) for g in val_groups],
            "test_groups": [str(g) for g in test_groups],
            "train_rows": len(train_df),
            "val_rows": len(val_df),
            "test_rows": len(test_df),
        }
        return train_df, val_df, test_df, meta

    # Default to CHRONOLOGICAL splitting
    sorted_df = df.copy()
    if "timestamp" in sorted_df.columns:
        sorted_df = sorted_df.sort_values(by="timestamp").reset_index(drop=True)

    train_end = int(total_rows * train_ratio)
    val_end = int(total_rows * (train_ratio + val_ratio))

    train_df = sorted_df.iloc[:train_end].reset_index(drop=True)
    val_df = sorted_df.iloc[train_end:val_end].reset_index(drop=True)
    test_df = sorted_df.iloc[val_end:].reset_index(drop=True)

    meta = {
        "strategy": "CHRONOLOGICAL",
        "total_rows": total_rows,
        "train_rows": len(train_df),
        "val_rows": len(val_df),
        "test_rows": len(test_df),
        "train_time_range": [str(train_df["timestamp"].iloc[0]), str(train_df["timestamp"].iloc[-1])] if not train_df.empty and "timestamp" in train_df else None,
        "test_time_range": [str(test_df["timestamp"].iloc[0]), str(test_df["timestamp"].iloc[-1])] if not test_df.empty and "timestamp" in test_df else None,
    }

    return train_df, val_df, test_df, meta
