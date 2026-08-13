"""
CROWDSHIELD TRAINING PIPELINE & REGISTRY TEST SUITE
===================================================
Tests real data loading, domain labeling strategy, versioned registry tracking,
and model rollback functionality.
"""

import os
import pytest
from app.ai.training.data_loader import load_historical_telemetry
from app.ai.training.label_strategy import apply_domain_labeling_and_weights
from app.ai.training.registry import (
    save_versioned_model,
    list_registered_models,
    get_active_model_path,
    rollback_model
)
from app.ai.risk_model import predict_risk, get_model


def test_data_loader_schema():
    """Verify data loader produces DataFrame matching feature vector schema."""
    df = load_historical_telemetry(num_samples=100)
    assert len(df) == 100
    assert "current_density" in df.columns
    assert "reverse_flow_ratio" in df.columns
    assert "blockage_score" in df.columns


def test_domain_labeling_and_weights():
    """Verify weak labeling identifies high-risk precursor states."""
    df = load_historical_telemetry(num_samples=50)
    y_current, y_precursor, weights = apply_domain_labeling_and_weights(df)

    assert len(y_current) == 50
    assert len(y_precursor) == 50
    assert len(weights) == 50
    # Positives must have higher weights than negatives
    pos_mask = y_precursor == 1
    if pos_mask.sum() > 0:
        assert weights[pos_mask].min() > weights[~pos_mask].max()


def test_model_registry_and_rollback():
    """Verify versioned model registration and rollback capabilities."""
    model = get_model()
    # Save a test version
    saved_path = save_versioned_model(model, {"test_metric": 0.95})
    assert os.path.exists(saved_path)

    models_list = list_registered_models()
    assert len(models_list) > 0
    assert any(m["is_active"] for m in models_list)

    # Rollback test
    active_before = get_active_model_path()
    rollback_path = rollback_model()
    assert os.path.exists(rollback_path)


def test_risk_prediction_with_retrained_model():
    """Verify risk prediction outputs normalized risk scores with active model."""
    sample_features = {
        "current_density": 0.82,
        "inflow_rate": 180.0,
        "outflow_rate": 40.0,
        "avg_pedestrian_speed": 0.35,
        "direction_conflict_score": 0.65,
        "gate_capacity_utilization": 0.85,
        "recent_incident_count_10min": 1.0,
        "reverse_flow_ratio": 0.45,
        "blockage_score": 0.50
    }
    risk_dict = predict_risk(sample_features)
    current_risk = risk_dict["current_risk"]
    predicted_5min = risk_dict["risk_5min"]
    assert 0.0 <= current_risk <= 100.0
    assert 0.0 <= predicted_5min <= 100.0
    # High density + low speed + reverse flow should trigger elevated risk (> 60.0)
    assert current_risk > 60.0
