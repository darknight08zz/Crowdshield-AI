"""
CROWDSHIELD DATASET AUDITOR & VALIDATOR (PHASE 4 - PARTS A, B, C, D)
=====================================================================
Audits and validates the versioned Phase 3 dataset prior to model training.
Verifies split integrity, missing values, timestamps, source distribution,
target class balances, and zero-leakage compliance.
"""

import os
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

from app.ai.dataset.schema import (
    CANDIDATE_MODEL_FEATURES,
    METADATA,
    IDENTIFIERS,
    TARGETS,
    PRIMARY_PROXY_TARGET
)
from app.ai.dataset.quality_validator import DatasetQualityValidator
from app.ai.dataset.provenance_filter import filter_telemetry_by_provenance, VALID_DATASET_MODES


class DatasetAuditReport:
    """Encapsulates dataset audit and validation results prior to model training."""

    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path
        self.exists: bool = False
        self.train_size: int = 0
        self.val_size: int = 0
        self.test_size: int = 0
        self.total_rows: int = 0
        self.feature_count: int = 0
        self.event_count: int = 0
        self.camera_count: int = 0
        self.zone_count: int = 0
        self.time_range: Dict[str, str] = {}
        self.source_distribution: Dict[str, int] = {}
        self.missing_value_count: int = 0
        self.target_stats: Dict[str, Dict[str, Any]] = {}
        self.source_mode: str = "MIXED_EXPLICIT"
        self.validation_result: Optional[Dict[str, Any]] = None
        self.split_overlap_detected: bool = False
        self.is_valid_for_training: bool = False
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_path": self.dataset_path,
            "exists": self.exists,
            "total_rows": self.total_rows,
            "feature_count": self.feature_count,
            "train_size": self.train_size,
            "val_size": self.val_size,
            "test_size": self.test_size,
            "event_count": self.event_count,
            "camera_count": self.camera_count,
            "zone_count": self.zone_count,
            "time_range": self.time_range,
            "source_distribution": self.source_distribution,
            "missing_value_count": self.missing_value_count,
            "target_stats": self.target_stats,
            "source_mode": self.source_mode,
            "split_overlap_detected": self.split_overlap_detected,
            "is_valid_for_training": self.is_valid_for_training,
            "quality_checks": self.validation_result or {}
        }


def audit_phase3_dataset(
    dataset_dir: str,
    source_mode: str = "MIXED_EXPLICIT"
) -> Tuple[DatasetAuditReport, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Loads, audits, and validates Phase 3 dataset splits.

    Returns:
        Tuple[DatasetAuditReport, train_df, val_df, test_df]
    """
    report = DatasetAuditReport(dataset_dir)
    report.source_mode = source_mode

    train_path = os.path.join(dataset_dir, "train_dataset.csv")
    val_path = os.path.join(dataset_dir, "val_dataset.csv")
    test_path = os.path.join(dataset_dir, "test_dataset.csv")
    meta_path = os.path.join(dataset_dir, "dataset_metadata.json")

    if not (os.path.exists(train_path) and os.path.exists(val_path) and os.path.exists(test_path)):
        report.exists = False
        report.is_valid_for_training = False
        return report, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    report.exists = True

    # Load Metadata if present
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                report.metadata = json.load(f)
        except Exception:
            report.metadata = {}

    # Load CSV splits
    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)
    test_df = pd.read_csv(test_path)

    # Apply Provenance Filter if configured
    if source_mode in VALID_DATASET_MODES:
        train_df = filter_telemetry_by_provenance(train_df, source_mode=source_mode)
        val_df = filter_telemetry_by_provenance(val_df, source_mode=source_mode)
        test_df = filter_telemetry_by_provenance(test_df, source_mode=source_mode)

    report.train_size = len(train_df)
    report.val_size = len(val_df)
    report.test_size = len(test_df)
    report.total_rows = report.train_size + report.val_size + report.test_size

    full_df = pd.concat([train_df, val_df, test_df], ignore_index=True)

    if len(full_df) == 0:
        report.is_valid_for_training = False
        return report, train_df, val_df, test_df

    # Basic stats
    available_features = [c for c in CANDIDATE_MODEL_FEATURES if c in full_df.columns]
    report.feature_count = len(available_features)

    report.event_count = int(full_df["event_id"].nunique()) if "event_id" in full_df.columns else 0
    report.camera_count = int(full_df["camera_id"].nunique()) if "camera_id" in full_df.columns else 0
    report.zone_count = int(full_df["zone_id"].nunique()) if "zone_id" in full_df.columns else 0

    if "timestamp" in full_df.columns:
        ts_sorted = pd.to_datetime(full_df["timestamp"]).sort_values()
        report.time_range = {
            "start": str(ts_sorted.iloc[0]),
            "end": str(ts_sorted.iloc[-1])
        }

    if "processing_mode" in full_df.columns:
        report.source_distribution = full_df["processing_mode"].value_counts().to_dict()

    report.missing_value_count = int(full_df[available_features].isna().sum().sum())

    # Audit targets (Part D)
    for target in TARGETS:
        if target in full_df.columns:
            pos_cnt = int((full_df[target] == 1).sum())
            neg_cnt = int((full_df[target] == 0).sum())
            total = len(full_df)
            pos_rate = float(pos_cnt / total) if total > 0 else 0.0

            is_trainable = (pos_cnt >= 5 and neg_cnt >= 5)
            report.target_stats[target] = {
                "positive_count": pos_cnt,
                "negative_count": neg_cnt,
                "positive_rate": round(pos_rate, 4),
                "status": "TRAINABLE" if is_trainable else "NOT_TRAINABLE_YET"
            }

    # Check split overlap / leakage (Part B)
    if "timestamp" in train_df.columns and "timestamp" in val_df.columns and "timestamp" in test_df.columns:
        train_keys = set(zip(train_df["timestamp"], train_df.get("zone_id", pd.Series(["Z0"] * len(train_df)))))
        val_keys = set(zip(val_df["timestamp"], val_df.get("zone_id", pd.Series(["Z0"] * len(val_df)))))
        test_keys = set(zip(test_df["timestamp"], test_df.get("zone_id", pd.Series(["Z0"] * len(test_df)))))

        overlap_tv = train_keys.intersection(val_keys)
        overlap_tt = train_keys.intersection(test_keys)
        report.split_overlap_detected = (len(overlap_tv) > 0 or len(overlap_tt) > 0)
    else:
        report.split_overlap_detected = False

    # Run dataset quality validator from Phase 3
    report.validation_result = DatasetQualityValidator(full_df).validate()

    val_status = report.validation_result.get("status") if report.validation_result else "FAILED"
    report.is_valid_for_training = (
        report.exists
        and report.train_size >= 10
        and not report.split_overlap_detected
        and val_status in ["PASS", "WARNING"]
    )

    return report, train_df, val_df, test_df
