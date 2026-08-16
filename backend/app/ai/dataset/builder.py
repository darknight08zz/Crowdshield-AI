"""
CROWDSHIELD REPRODUCIBLE DATASET BUILDER
========================================
Main orchestrator for generating leak-free ML datasets from raw telemetry logs.

WORKFLOW:
1. Ingest telemetry log rows (CSV / DB / Ingestion stream).
2. Validate initial telemetry quality.
3. Filter by dataset provenance mode (REAL_ONLY, DEMO_VIDEO, SYNTHETIC, MIXED_EXPLICIT).
4. Sort chronologically by event/zone and timestamp.
5. Construct temporal feature windows (rolling statistics, temporal derivatives).
6. Assign multi-horizon prediction target labels (2m, 5m, 10m).
7. Apply leakage-free dataset splitting (Chronological or Event-level).
8. Compute feature scaling parameters strictly on training split.
9. Validate final output dataset.
10. Save dataset artifacts and metadata JSON.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np

from app.ai.dataset.schema import (
    FEATURE_SCHEMA_VERSION,
    LABEL_SCHEMA_VERSION,
    DATASET_VERSION,
    CANONICAL_FEATURE_SCHEMA,
    CANDIDATE_MODEL_FEATURES,
)
from app.ai.dataset.provenance_filter import filter_telemetry_by_provenance
from app.ai.dataset.missing_data import handle_missing_telemetry
from app.ai.dataset.feature_extractor import (
    calculate_derived_temporal_features,
    compute_target_labels,
    compute_row_physics_risk,
)
from app.ai.dataset.splitter import split_dataset_leakage_free
from app.ai.dataset.scaler_prep import compute_training_scaler_params
from app.ai.dataset.quality_validator import DatasetQualityValidator


class DatasetBuilder:
    """
    Reproducible ML dataset builder for CrowdShield.
    """

    def __init__(
        self,
        feature_window_seconds: int = 300,
        prediction_horizon_seconds: int = 300,
        source_mode: str = "MIXED_EXPLICIT",
        split_strategy: str = "CHRONOLOGICAL"
    ):
        self.feature_window_seconds = feature_window_seconds
        self.prediction_horizon_seconds = prediction_horizon_seconds
        self.source_mode = source_mode
        self.split_strategy = split_strategy

    def build_dataset(
        self,
        telemetry_df: pd.DataFrame,
        sec_per_sample: float = 10.0
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Builds complete ML dataset from raw telemetry DataFrame.

        Returns:
            Tuple[train_df, val_df, test_df, metadata_dict]
        """
        if telemetry_df is None or telemetry_df.empty:
            raise ValueError("Input telemetry_df is empty or None.")

        # 1. Filter provenance
        filtered_df = filter_telemetry_by_provenance(telemetry_df, source_mode=self.source_mode)
        if filtered_df.empty:
            raise ValueError(f"No telemetry records remained after applying provenance filter mode: {self.source_mode}")

        # 2. Handle missing telemetry
        cleaned_df, missing_report = handle_missing_telemetry(filtered_df)

        # 3. Sort chronologically by zone and timestamp
        if "zone_id" in cleaned_df.columns and "timestamp" in cleaned_df.columns:
            cleaned_df = cleaned_df.sort_values(by=["zone_id", "timestamp"]).reset_index(drop=True)

        # 4. Temporal windowing & target assignment
        processed_rows: List[Dict[str, Any]] = []
        zones = cleaned_df["zone_id"].unique() if "zone_id" in cleaned_df.columns else ["default_zone"]

        for zone_id in zones:
            zone_sub = cleaned_df[cleaned_df["zone_id"] == zone_id].reset_index(drop=True) if "zone_id" in cleaned_df.columns else cleaned_df.reset_index(drop=True)
            num_zone_rows = len(zone_sub)

            # Precompute risk scores for sub-second target lookup across all future horizons
            zone_risk_scores = np.array([compute_row_physics_risk(zone_sub.iloc[idx]) for idx in range(num_zone_rows)])

            for i in range(num_zone_rows):
                row = zone_sub.iloc[i].to_dict()

                # Calculate non-leaking derived temporal features up to row index i
                derived_feats = calculate_derived_temporal_features(zone_sub, current_idx=i)
                row.update(derived_feats)

                # Compute target labels looking forward from index i
                targets = compute_target_labels(
                    zone_sub,
                    current_idx=i,
                    sec_per_sample=sec_per_sample,
                    precomputed_risk_scores=zone_risk_scores
                )
                row.update(targets)

                processed_rows.append(row)

        full_dataset_df = pd.DataFrame(processed_rows)

        # 5. Validate dataset quality
        validator = DatasetQualityValidator(full_dataset_df)
        val_report = validator.validate()

        # 6. Leakage-free dataset splitting
        train_df, val_df, test_df, split_meta = split_dataset_leakage_free(
            full_dataset_df,
            strategy=self.split_strategy,
            train_ratio=0.70,
            val_ratio=0.15
        )

        # 7. Compute scaling parameters strictly on training split
        scaler_params = compute_training_scaler_params(train_df, features=CANDIDATE_MODEL_FEATURES)

        metadata = {
            "dataset_version": DATASET_VERSION,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "label_schema_version": LABEL_SCHEMA_VERSION,
            "creation_timestamp": datetime.utcnow().isoformat() + "Z",
            "feature_window_seconds": self.feature_window_seconds,
            "prediction_horizon_seconds": self.prediction_horizon_seconds,
            "source_mode": self.source_mode,
            "split_strategy": self.split_strategy,
            "total_rows": len(full_dataset_df),
            "missing_data_report": missing_report,
            "quality_validation_report": val_report,
            "split_metadata": split_meta,
            "training_scaler_params": scaler_params,
            "ground_truth_status": "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
            "label_type": "PROXY",
            "model_training_status": "NOT_PERFORMED",
        }

        return train_df, val_df, test_df, metadata

    def save_dataset_artifacts(
        self,
        output_dir: str,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
        metadata: Dict[str, Any]
    ) -> Tuple[str, str, str, str]:
        """
        Saves dataset splits to CSV files and exports metadata JSON.
        """
        os.makedirs(output_dir, exist_ok=True)

        train_path = os.path.join(output_dir, "train_dataset.csv")
        val_path = os.path.join(output_dir, "val_dataset.csv")
        test_path = os.path.join(output_dir, "test_dataset.csv")
        meta_path = os.path.join(output_dir, "dataset_metadata.json")

        train_df.to_csv(train_path, index=False)
        val_df.to_csv(val_path, index=False)
        test_df.to_csv(test_path, index=False)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return train_path, val_path, test_path, meta_path
