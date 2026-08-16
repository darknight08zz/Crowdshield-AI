"""
CROWDSHIELD CANONICAL ML FEATURE SCHEMA V2.0 (PHASE 5)
======================================================
Defines Dataset V2 feature schemas, temporal targets, and metadata boundaries
for Phase 5 Temporal Early-Warning Intelligence.
"""

from typing import List, Dict, Any

# Dataset & Schema Versions
FEATURE_SCHEMA_VERSION_V2 = "v2.0"
LABEL_SCHEMA_VERSION_V2 = "v2.0"
DATASET_VERSION_V2 = "v2.0"

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

DERIVED_TEMPORAL_FEATURES: List[str] = [
    "flow_imbalance",
    "net_accumulation",
    "density_change",
    "density_rate",
    "density_acceleration",
    "speed_change",
    "speed_rate",
    "speed_acceleration",
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

# Phase 5 Candidate Targets
PHASE_5_TARGETS: List[str] = [
    "RISK_DELTA_5M",            # Continuous change: Risk(t+5m) - Risk(t)
    "RISK_DELTA_5M_CLASS",      # Binned: NO_ESCALATION, MODERATE_ESCALATION, STRONG_ESCALATION
    "EARLY_ESCALATION_5M",      # Binary: 1 if dynamic crowd deterioration occurs in future window, else 0
    "RISK_AT_5M",               # Continuous future risk score: Risk(t+5m)
]

PRIMARY_TEMPORAL_TARGET: str = "EARLY_ESCALATION_5M"
PRIMARY_REGRESSION_TARGET: str = "RISK_DELTA_5M"

# Candidate Features for Model Training
CANDIDATE_TEMPORAL_FEATURES: List[str] = RAW_FEATURES + DERIVED_TEMPORAL_FEATURES

# Threshold & Terminology Standards (Phase 5B)
MODEL_TRAINING_THRESHOLD: float = 0.05
DEFAULT_OPERATIONAL_ALERT_THRESHOLD: float = 0.50

# Explicit Target Metadata (Phase 5B Requirement 8)
TARGET_METADATA_V1: Dict[str, Any] = {
    "target_name": PRIMARY_TEMPORAL_TARGET,
    "target_version": "1.0",
    "horizon_seconds": 300,
    "label_type": "PHYSICS_DEFINED_PROXY",
    "target_definition_hash": "a4d9e7f81b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e",
    "description": "Binary dynamic deterioration indicator derived from trajectory escalation physics rules."
}

# Enforced Terminology (Phase 5B Requirement 7)
ALLOWED_PROXY_TERMINOLOGY: List[str] = [
    "PHYSICS_DEFINED_PROXY",
    "PROXY_TEMPORAL_ESCALATION",
    "PROTOTYPE_EARLY_WARNING",
    "SIMULATED_PHYSICS_GROUND_TRUTH"
]

FORBIDDEN_CLAIM_TERMINOLOGY: List[str] = [
    "REAL_STAMPEDE_PREDICTION",
    "REAL_INCIDENT_PREDICTION",
    "CLINICAL_PREDICTION",
    "VALIDATED_SAFETY_PREDICTION"
]

CANONICAL_FEATURE_SCHEMA_V2: Dict[str, Any] = {
    "feature_schema_version": FEATURE_SCHEMA_VERSION_V2,
    "label_schema_version": LABEL_SCHEMA_VERSION_V2,
    "dataset_version": DATASET_VERSION_V2,
    "identifiers": IDENTIFIERS,
    "raw_features": RAW_FEATURES,
    "derived_temporal_features": DERIVED_TEMPORAL_FEATURES,
    "metadata": METADATA,
    "phase_5_targets": PHASE_5_TARGETS,
    "candidate_temporal_features": CANDIDATE_TEMPORAL_FEATURES,
    "target_metadata": TARGET_METADATA_V1,
    "model_training_threshold": MODEL_TRAINING_THRESHOLD,
    "default_operational_alert_threshold": DEFAULT_OPERATIONAL_ALERT_THRESHOLD,
    "description": "V2.0 dataset schema for temporal early-warning forecasting in Phase 5.",
}
