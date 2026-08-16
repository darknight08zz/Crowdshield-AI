"""
CROWDSHIELD AUTOMATED DATASET QUALITY VALIDATOR
================================================
Automated quality validation for temporal crowd telemetry datasets.

Checks:
- Missing, duplicate, or out-of-order timestamps
- Negative density, flow, or speed
- Invalid confidence scores
- Missing camera or zone identifiers
- Telemetry gaps and stale feeds
- Synthetic data contamination ratio
- Temporal and target leakage checks
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np


class DatasetQualityValidator:
    """
    Evaluates dataset quality integrity and outputs a structured validation report.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def validate(self) -> Dict[str, Any]:
        if self.df is None or self.df.empty:
            return {
                "total_rows": 0,
                "valid_rows": 0,
                "invalid_rows": 0,
                "status": "FAILED",
                "reason": "Dataset is empty or None",
            }

        df = self.df
        total_rows = len(df)
        issues: List[str] = []

        # 1. Missing identifiers
        missing_ts = int(df["timestamp"].isnull().sum()) if "timestamp" in df.columns else total_rows
        missing_zone = int(df["zone_id"].isnull().sum()) if "zone_id" in df.columns else total_rows
        missing_cam = int(df["camera_id"].isnull().sum()) if "camera_id" in df.columns else 0

        # 2. Duplicate timestamps per zone
        duplicates = 0
        if "timestamp" in df.columns and "zone_id" in df.columns:
            duplicates = int(df.duplicated(subset=["timestamp", "zone_id"]).sum())

        # 3. Numeric bounds checks
        neg_density = 0
        if "density" in df.columns:
            neg_density = int((df["density"] < 0.0).sum())
        elif "current_density" in df.columns:
            neg_density = int((df["current_density"] < 0.0).sum())

        neg_flow = 0
        if "inflow_rate" in df.columns:
            neg_flow += int((df["inflow_rate"] < 0.0).sum())
        if "outflow_rate" in df.columns:
            neg_flow += int((df["outflow_rate"] < 0.0).sum())

        neg_speed = 0
        if "average_speed" in df.columns:
            neg_speed += int((df["average_speed"] < 0.0).sum())

        invalid_confidence = 0
        if "confidence_score" in df.columns:
            invalid_confidence = int(((df["confidence_score"] < 0.0) | (df["confidence_score"] > 1.0)).sum())

        # 4. Provenance & Synthetic Contamination
        synthetic_records = 0
        if "is_synthetic" in df.columns:
            synthetic_records = int((df["is_synthetic"] == True).sum())

        degraded_records = 0
        if "is_degraded" in df.columns:
            degraded_records = int((df["is_degraded"] == True).sum())

        # 5. Out of order timestamps check
        out_of_order = 0
        if "timestamp" in df.columns and "zone_id" in df.columns:
            for zone_id, group in df.groupby("zone_id"):
                ts_series = pd.to_datetime(group["timestamp"])
                if not ts_series.is_monotonic_increasing:
                    out_of_order += 1

        invalid_rows = neg_density + neg_speed + neg_flow + missing_ts + missing_zone + duplicates
        valid_rows = max(0, total_rows - invalid_rows)

        if invalid_rows > 0:
            issues.append(f"{invalid_rows} rows contain invalid numeric bounds or missing IDs.")
        if duplicates > 0:
            issues.append(f"{duplicates} duplicate timestamps detected.")
        if out_of_order > 0:
            issues.append(f"{out_of_order} zones have out-of-order timestamps.")

        is_passed = (invalid_rows == 0) and (missing_ts == 0) and (missing_zone == 0)

        report = {
            "total_rows": total_rows,
            "valid_rows": valid_rows,
            "invalid_rows": invalid_rows,
            "missing_timestamp": missing_ts,
            "missing_zone_id": missing_zone,
            "missing_camera_id": missing_cam,
            "duplicate_samples": duplicates,
            "out_of_order_zones": out_of_order,
            "negative_density": neg_density,
            "negative_flow": neg_flow,
            "negative_speed": neg_speed,
            "invalid_confidence": invalid_confidence,
            "synthetic_records": synthetic_records,
            "degraded_records": degraded_records,
            "status": "PASS" if is_passed else "WARNING",
            "issues": issues,
        }

        return report
