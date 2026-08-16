"""
DATASET BUILDER V2.0 (PHASE 5)
===============================
Orchestrates Dataset V2 construction with temporal windowing, boundary protection,
Phase 5 candidate target generation, provenance tagging, and leakage-free splitting.
"""

from typing import Dict, List, Tuple, Any, Optional
import os
import json
import pandas as pd
import numpy as np

from app.ai.dataset.schema_v2 import (
    DATASET_VERSION_V2,
    FEATURE_SCHEMA_VERSION_V2,
    LABEL_SCHEMA_VERSION_V2,
    CANDIDATE_TEMPORAL_FEATURES,
    PHASE_5_TARGETS,
    PRIMARY_TEMPORAL_TARGET,
)
from app.ai.dataset.schema import SAFE_BASELINES
from app.ai.dataset.temporal_feature_extractor import (
    extract_temporal_derivatives_and_accelerations,
    compute_phase5_targets,
    build_temporal_sequence_samples,
)


class DatasetBuilderV2:
    def __init__(self, data_dir: str = "data/dataset_v2"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def load_raw_telemetry(self, file_path: str) -> pd.DataFrame:
        """Loads raw telemetry from CSV or parquet."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Telemetry file not found at: {file_path}")
        return pd.read_csv(file_path)

    def filter_by_provenance(self, df: pd.DataFrame, allowed_sources: Optional[List[str]] = None) -> pd.DataFrame:
        """Filters dataset based on allowed telemetry sources."""
        if allowed_sources is None:
            allowed_sources = ["LIVE", "MIXED_EXPLICIT", "REAL_ONLY", "BENCHMARK_VIDEO", "DEMO_VIDEO"]

        if "telemetry_source" in df.columns:
            filtered = df[df["telemetry_source"].isin(allowed_sources)].copy()
            if len(filtered) > 0:
                return filtered
        return df.copy()

    def impute_missing_telemetry(self, df: pd.DataFrame) -> pd.DataFrame:
        """Forward-fills missing values within zone groups, then applies safe defaults."""
        df = df.copy()
        group_cols = [col for col in ["event_id", "camera_id", "zone_id"] if col in df.columns]

        if group_cols:
            df = df.groupby(group_cols, group_keys=False).apply(lambda g: g.ffill().bfill())

        for col, default_val in SAFE_BASELINES.items():
            if col in df.columns:
                df[col] = df[col].fillna(default_val)
            elif col in CANDIDATE_TEMPORAL_FEATURES:
                df[col] = default_val

        return df

    def build_dataset_v2(
        self,
        raw_df: pd.DataFrame,
        horizon_steps: int = 30,
        allowed_sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Main pipeline execution to build Dataset V2.
        """
        # 1. Provenance Filter
        df = self.filter_by_provenance(raw_df, allowed_sources)

        # 2. Sort chronologically
        sort_cols = [col for col in ["event_id", "camera_id", "zone_id", "timestamp"] if col in df.columns]
        if sort_cols:
            df = df.sort_values(sort_cols).reset_index(drop=True)

        # 3. Impute missing values
        df = self.impute_missing_telemetry(df)

        # 4. Extract temporal derivatives and accelerations
        df = extract_temporal_derivatives_and_accelerations(df)

        # 5. Compute Phase 5 Targets
        df = compute_phase5_targets(df, horizon_steps=horizon_steps)

        # 6. Drop rows where target is NaN (due to forward window boundary)
        clean_df = df.dropna(subset=[PRIMARY_TEMPORAL_TARGET]).reset_index(drop=True)

        # 7. Analyze Independent Events
        unique_events = clean_df["event_id"].nunique() if "event_id" in clean_df.columns else 1
        unique_cameras = clean_df["camera_id"].nunique() if "camera_id" in clean_df.columns else 1
        unique_zones = clean_df["zone_id"].nunique() if "zone_id" in clean_df.columns else 1

        # 8. Leakage-Free Dataset Splitting
        if unique_events >= 2:
            event_ids = clean_df["event_id"].unique()
            train_events = event_ids[: int(0.7 * len(event_ids))]
            val_events = event_ids[int(0.7 * len(event_ids)) : int(0.85 * len(event_ids))]
            test_events = event_ids[int(0.85 * len(event_ids)) :]

            train_df = clean_df[clean_df["event_id"].isin(train_events)].reset_index(drop=True)
            val_df = clean_df[clean_df["event_id"].isin(val_events)].reset_index(drop=True)
            test_df = clean_df[clean_df["event_id"].isin(test_events)].reset_index(drop=True)
            split_strategy = "EVENT_LEVEL"
            generalization_status = "VALIDATED_MULTI_EVENT"
        else:
            # Safe Chronological Split
            n = len(clean_df)
            n_train = int(0.70 * n)
            n_val = int(0.15 * n)

            train_df = clean_df.iloc[:n_train].reset_index(drop=True)
            val_df = clean_df.iloc[n_train : n_train + n_val].reset_index(drop=True)
            test_df = clean_df.iloc[n_train + n_val :].reset_index(drop=True)
            split_strategy = "CHRONOLOGICAL"
            generalization_status = "INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION"

        # 9. Save CSV files
        full_path = os.path.join(self.data_dir, "dataset_v2_full.csv")
        train_path = os.path.join(self.data_dir, "train_dataset.csv")
        val_path = os.path.join(self.data_dir, "val_dataset.csv")
        test_path = os.path.join(self.data_dir, "test_dataset.csv")

        clean_df.to_csv(full_path, index=False)
        train_df.to_csv(train_path, index=False)
        val_df.to_csv(val_path, index=False)
        test_df.to_csv(test_path, index=False)

        # 10. Generate & Save Metadata
        metadata = {
            "dataset_version": DATASET_VERSION_V2,
            "feature_schema_version": FEATURE_SCHEMA_VERSION_V2,
            "label_schema_version": LABEL_SCHEMA_VERSION_V2,
            "total_samples": len(clean_df),
            "train_samples": len(train_df),
            "val_samples": len(val_df),
            "test_samples": len(test_df),
            "unique_events": unique_events,
            "unique_cameras": unique_cameras,
            "unique_zones": unique_zones,
            "split_strategy": split_strategy,
            "generalization_status": generalization_status,
            "primary_target": PRIMARY_TEMPORAL_TARGET,
            "horizon_steps": horizon_steps,
            "horizon_seconds": horizon_steps * 10,
            "candidate_features": CANDIDATE_TEMPORAL_FEATURES,
            "target_distribution": {
                "EARLY_ESCALATION_5M": {
                    "total_positive": int(clean_df[PRIMARY_TEMPORAL_TARGET].sum()),
                    "total_negative": int(len(clean_df) - clean_df[PRIMARY_TEMPORAL_TARGET].sum()),
                    "positive_ratio": float(clean_df[PRIMARY_TEMPORAL_TARGET].mean()),
                },
                "RISK_DELTA_5M": {
                    "mean": float(clean_df["RISK_DELTA_5M"].mean()),
                    "median": float(clean_df["RISK_DELTA_5M"].median()),
                    "std": float(clean_df["RISK_DELTA_5M"].std()),
                    "min": float(clean_df["RISK_DELTA_5M"].min()),
                    "max": float(clean_df["RISK_DELTA_5M"].max()),
                }
            }
        }

        meta_path = os.path.join(self.data_dir, "dataset_metadata.json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return {
            "full_df": clean_df,
            "train_df": train_df,
            "val_df": val_df,
            "test_df": test_df,
            "metadata": metadata,
        }
