"""
TEST SUITE FOR DATASET BUILDER & LEAKAGE PREVENTION (PHASE 3)
=============================================================
Comprehensive automated tests verifying dataset schema, windowing, target labels,
leakage prevention, quality validation, scaling, and CLI tools.
"""

import os
import shutil
import json
import pytest
import pandas as pd
import numpy as np

from app.ai.dataset.schema import (
    FEATURE_SCHEMA_VERSION,
    LABEL_SCHEMA_VERSION,
    DATASET_VERSION,
    IDENTIFIERS,
    RAW_FEATURES,
    DERIVED_FEATURES,
    METADATA,
    TARGETS,
    CANDIDATE_MODEL_FEATURES,
)
from app.ai.dataset.feature_extractor import calculate_derived_temporal_features, compute_target_labels
from app.ai.dataset.provenance_filter import filter_telemetry_by_provenance
from app.ai.dataset.missing_data import handle_missing_telemetry
from app.ai.dataset.splitter import split_dataset_leakage_free
from app.ai.dataset.scaler_prep import compute_training_scaler_params
from app.ai.dataset.quality_validator import DatasetQualityValidator
from app.ai.dataset.builder import DatasetBuilder
from scripts.build_dataset import generate_synthetic_telemetry


def test_canonical_feature_schema_integrity():
    """
    Verifies that the canonical feature schema contains all required feature groups and versioning tags.
    """
    assert FEATURE_SCHEMA_VERSION == "v1.0"
    assert LABEL_SCHEMA_VERSION == "v1.0"
    assert DATASET_VERSION == "v1.0"

    assert "density" in RAW_FEATURES
    assert "average_speed" in RAW_FEATURES
    assert "direction_conflict_score" in RAW_FEATURES
    assert "reverse_flow_ratio" in RAW_FEATURES

    assert "density_change" in DERIVED_FEATURES
    assert "speed_change" in DERIVED_FEATURES
    assert "rolling_density_mean" in DERIVED_FEATURES
    assert "flow_imbalance" in DERIVED_FEATURES

    assert "HIGH_RISK_WITHIN_2M" in TARGETS
    assert "HIGH_RISK_WITHIN_5M" in TARGETS
    assert "HIGH_RISK_WITHIN_10M" in TARGETS
    assert "HIGH_RISK_STATE_TRANSITION_PROXY" in TARGETS

    assert len(CANDIDATE_MODEL_FEATURES) == len(RAW_FEATURES) + len(DERIVED_FEATURES)


def test_provenance_filtering_modes():
    """
    Verifies strict provenance filtering for REAL_ONLY, DEMO_VIDEO, SYNTHETIC, and MIXED_EXPLICIT datasets.
    """
    sample_df = pd.DataFrame([
        {"timestamp": "2026-08-14T10:00:00Z", "processing_mode": "LIVE", "is_synthetic": False, "is_simulated": False},
        {"timestamp": "2026-08-14T10:00:10Z", "processing_mode": "DEMO", "is_synthetic": False, "is_simulated": False},
        {"timestamp": "2026-08-14T10:00:20Z", "processing_mode": "LIVE", "is_synthetic": True, "is_simulated": False},
    ])

    real_df = filter_telemetry_by_provenance(sample_df, source_mode="REAL_ONLY")
    assert len(real_df) == 1
    assert real_df.iloc[0]["processing_mode"] == "LIVE"
    assert bool(real_df.iloc[0]["is_synthetic"]) is False

    demo_df = filter_telemetry_by_provenance(sample_df, source_mode="DEMO_VIDEO")
    assert len(demo_df) == 1
    assert demo_df.iloc[0]["processing_mode"] == "DEMO"

    synth_df = filter_telemetry_by_provenance(sample_df, source_mode="SYNTHETIC")
    assert len(synth_df) == 1
    assert bool(synth_df.iloc[0]["is_synthetic"]) is True

    mixed_df = filter_telemetry_by_provenance(sample_df, source_mode="MIXED_EXPLICIT")
    assert len(mixed_df) == 3


def test_temporal_feature_extraction_no_future_leakage():
    """
    Verifies that temporal window derived features at index i DO NOT consume future row observations (i+1 to N).
    """
    telemetry = generate_synthetic_telemetry(num_samples=100)
    zone_sub = telemetry[telemetry["zone_id"] == "ZONE-NORTH"].reset_index(drop=True)

    # Compute derived features for index 10 using full sequence dataframe vs truncated dataframe
    df_full = zone_sub.copy()
    df_trunc = zone_sub.iloc[:11].copy()  # Only rows 0..10

    feats_full = calculate_derived_temporal_features(df_full, current_idx=10)
    feats_trunc = calculate_derived_temporal_features(df_trunc, current_idx=10)

    # Derived features at t=10 must be EXACTLY identical whether future data exists or not
    for k in feats_full.keys():
        assert feats_full[k] == feats_trunc[k], f"Feature '{k}' leaked future data!"


def test_target_label_proxy_metadata():
    """
    Verifies that prediction target labels contain proxy label flags and unvalidated ground-truth warnings.
    """
    telemetry = generate_synthetic_telemetry(num_samples=100)
    zone_sub = telemetry[telemetry["zone_id"] == "ZONE-NORTH"].reset_index(drop=True)

    targets = compute_target_labels(zone_sub, current_idx=10)

    assert targets["label_type"] == "PROXY"
    assert targets["ground_truth_status"] == "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED"
    assert targets["HIGH_RISK_WITHIN_2M"] in [0, 1]
    assert targets["HIGH_RISK_WITHIN_5M"] in [0, 1]
    assert targets["HIGH_RISK_WITHIN_10M"] in [0, 1]
    assert targets["HIGH_RISK_STATE_TRANSITION_PROXY"] in [0, 1]


def test_leakage_free_chronological_and_event_splitting():
    """
    Verifies that dataset splitting enforces chronological order or event-level isolation.
    """
    telemetry = generate_synthetic_telemetry(num_samples=200)

    # Chronological split test
    train_df, val_df, test_df, meta_chron = split_dataset_leakage_free(
        telemetry, strategy="CHRONOLOGICAL", train_ratio=0.70, val_ratio=0.15
    )

    assert len(train_df) + len(val_df) + len(test_df) == len(telemetry)
    assert meta_chron["strategy"] == "CHRONOLOGICAL"

    # Verify no timestamp overlap between train, val, and test
    train_max_ts = pd.to_datetime(train_df["timestamp"]).max()
    val_min_ts = pd.to_datetime(val_df["timestamp"]).min()
    val_max_ts = pd.to_datetime(val_df["timestamp"]).max()
    test_min_ts = pd.to_datetime(test_df["timestamp"]).min()

    assert train_max_ts <= val_min_ts
    assert val_max_ts <= test_min_ts

    # Event-level split test
    telemetry["event_id"] = np.random.choice(["EVENT-1", "EVENT-2", "EVENT-3", "EVENT-4"], size=len(telemetry))
    train_ev, val_ev, test_ev, meta_ev = split_dataset_leakage_free(
        telemetry, strategy="EVENT_LEVEL", group_col="event_id", train_ratio=0.50, val_ratio=0.25
    )

    assert meta_ev["strategy"] == "EVENT_LEVEL"
    train_events = set(train_ev["event_id"].unique())
    val_events = set(val_ev["event_id"].unique())
    test_events = set(test_ev["event_id"].unique())

    # Verify event IDs do not leak across splits
    assert train_events.isdisjoint(val_events)
    assert train_events.isdisjoint(test_events)
    assert val_events.isdisjoint(test_events)


def test_scaler_parameters_fitted_strictly_on_train_split():
    """
    Verifies that feature scaling parameters are computed strictly on the training split.
    """
    train_data = pd.DataFrame({"density": [0.1, 0.2, 0.3], "average_speed": [1.0, 1.2, 1.4]})
    test_data = pd.DataFrame({"density": [0.8, 0.9, 1.0], "average_speed": [0.2, 0.1, 0.0]})

    scaler_params = compute_training_scaler_params(train_data, features=["density", "average_speed"])

    # Mean of density on train set is 0.2 (0.1+0.2+0.3 / 3)
    assert pytest.approx(scaler_params["density"]["mean"], 0.001) == 0.20
    assert scaler_params["density"]["min"] == 0.10
    assert scaler_params["density"]["max"] == 0.30


def test_dataset_quality_validator_reporting():
    """
    Verifies that DatasetQualityValidator correctly flags negative density, invalid scores, or duplicate timestamps.
    """
    invalid_df = pd.DataFrame([
        {"timestamp": "2026-08-14T10:00:00Z", "zone_id": "ZONE-A", "camera_id": "CAM-1", "density": -0.5, "average_speed": 1.2, "confidence_score": 0.9},
        {"timestamp": "2026-08-14T10:00:00Z", "zone_id": "ZONE-A", "camera_id": "CAM-1", "density": 0.4, "average_speed": -0.2, "confidence_score": 1.5},
    ])

    validator = DatasetQualityValidator(invalid_df)
    report = validator.validate()

    assert report["status"] in ["WARNING", "FAILED"]
    assert report["negative_density"] == 1
    assert report["negative_speed"] == 1
    assert report["invalid_confidence"] == 1
    assert report["duplicate_samples"] == 1


def test_reproducible_dataset_builder_end_to_end(tmp_path):
    """
    Verifies that running DatasetBuilder twice with identical parameters produces identical datasets.
    """
    telemetry = generate_synthetic_telemetry(num_samples=200)

    builder = DatasetBuilder(
        feature_window_seconds=300,
        prediction_horizon_seconds=300,
        source_mode="MIXED_EXPLICIT",
        split_strategy="CHRONOLOGICAL"
    )

    out_dir_1 = str(tmp_path / "run_1")
    out_dir_2 = str(tmp_path / "run_2")

    tr1, val1, ts1, meta1 = builder.build_dataset(telemetry)
    builder.save_dataset_artifacts(out_dir_1, tr1, val1, ts1, meta1)

    tr2, val2, ts2, meta2 = builder.build_dataset(telemetry)
    builder.save_dataset_artifacts(out_dir_2, tr2, val2, ts2, meta2)

    # Check identical row counts & feature values
    assert len(tr1) == len(tr2)
    assert len(val1) == len(val2)
    assert len(ts1) == len(ts2)

    # Compare train CSV content
    train_csv_1 = pd.read_csv(os.path.join(out_dir_1, "train_dataset.csv"))
    train_csv_2 = pd.read_csv(os.path.join(out_dir_2, "train_dataset.csv"))

    pd.testing.assert_frame_equal(train_csv_1, train_csv_2)
    assert meta1["ground_truth_status"] == "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED"
    assert meta1["model_training_status"] == "NOT_PERFORMED"
