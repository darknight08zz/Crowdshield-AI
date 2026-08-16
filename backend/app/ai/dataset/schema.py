"""
CROWDSHIELD CANONICAL ML FEATURE SCHEMA
=======================================
Defines explicit feature boundaries, version metadata, provenance metadata,
candidate model inputs, and multi-horizon target labels.
"""

from typing import List, Dict, Any

# Dataset & Schema Versions
FEATURE_SCHEMA_VERSION = "v1.0"
LABEL_SCHEMA_VERSION = "v1.0"
DATASET_VERSION = "v1.0"

# Category Definitions
IDENTIFIERS: List[str] = [
    "timestamp",
    "camera_id",
    "zone_id",
    "event_id",
]

RAW_FEATURES: List[str] = [
    "density",
    "inflow_rate",
    "outflow_rate",
    "average_speed",
    "median_speed",
    "stationary_ratio",
    "reverse_flow_ratio",
    "direction_conflict_score",
    "blockage_score",
    "person_count",
    "tracked_person_count",
]

DERIVED_FEATURES: List[str] = [
    "flow_imbalance",
    "net_accumulation",
    "density_change",
    "density_rate",
    "speed_change",
    "speed_rate",
    "inflow_change",
    "outflow_change",
    "rolling_density_mean",
    "rolling_density_std",
    "rolling_speed_mean",
    "rolling_speed_std",
]

METADATA: List[str] = [
    "calibration_status",
    "telemetry_source",
    "processing_mode",
    "confidence_score",
    "is_degraded",
    "is_synthetic",
    "is_simulated",
]

TARGETS: List[str] = [
    "HIGH_RISK_WITHIN_2M",
    "HIGH_RISK_WITHIN_5M",
    "HIGH_RISK_WITHIN_10M",
    "HIGH_RISK_STATE_TRANSITION_PROXY",
]

PRIMARY_PROXY_TARGET: str = "HIGH_RISK_STATE_TRANSITION_PROXY"

# Candidate Features for Model Training (Excludes metadata, IDs, and future leakage targets)
CANDIDATE_MODEL_FEATURES: List[str] = RAW_FEATURES + DERIVED_FEATURES

SAFE_BASELINES: Dict[str, float] = {
    "density": 0.20,
    "inflow_rate": 60.0,
    "outflow_rate": 60.0,
    "average_speed": 1.20,
    "median_speed": 1.20,
    "stationary_ratio": 0.05,
    "reverse_flow_ratio": 0.02,
    "direction_conflict_score": 0.05,
    "blockage_score": 0.05,
    "person_count": 50,
    "tracked_person_count": 50,
    "flow_imbalance": 0.0,
    "net_accumulation": 0.0,
    "density_change": 0.0,
    "density_rate": 0.0,
    "speed_change": 0.0,
    "speed_rate": 0.0,
    "inflow_change": 0.0,
    "outflow_change": 0.0,
    "rolling_density_mean": 0.20,
    "rolling_density_std": 0.01,
    "rolling_speed_mean": 1.20,
    "rolling_speed_std": 0.01
}

CANONICAL_FEATURE_SCHEMA: Dict[str, Any] = {
    "feature_schema_version": FEATURE_SCHEMA_VERSION,
    "label_schema_version": LABEL_SCHEMA_VERSION,
    "identifiers": IDENTIFIERS,
    "raw_features": RAW_FEATURES,
    "derived_features": DERIVED_FEATURES,
    "metadata": METADATA,
    "targets": TARGETS,
    "candidate_model_features": CANDIDATE_MODEL_FEATURES,
    "description": "Canonical dataset feature schema produced by Phase 2 CV pipeline for Phase 3 ML preparation.",
}
