"""
CROWDSHIELD DATASET & FEATURE FOUNDATION (PHASE 3)
================================================
Package for canonical ML feature extraction, dataset windowing, labeling strategy,
provenance filtering, quality validation, leakage prevention, and dataset versioning.
"""

from app.ai.dataset.schema import (
    FEATURE_SCHEMA_VERSION,
    LABEL_SCHEMA_VERSION,
    DATASET_VERSION,
    CANONICAL_FEATURE_SCHEMA,
    IDENTIFIERS,
    RAW_FEATURES,
    DERIVED_FEATURES,
    METADATA,
    TARGETS,
)
from app.ai.dataset.builder import DatasetBuilder
from app.ai.dataset.quality_validator import DatasetQualityValidator
from app.ai.dataset.baseline_engine import baseline_risk

__all__ = [
    "FEATURE_SCHEMA_VERSION",
    "LABEL_SCHEMA_VERSION",
    "DATASET_VERSION",
    "CANONICAL_FEATURE_SCHEMA",
    "IDENTIFIERS",
    "RAW_FEATURES",
    "DERIVED_FEATURES",
    "METADATA",
    "TARGETS",
    "DatasetBuilder",
    "DatasetQualityValidator",
    "baseline_risk",
]
