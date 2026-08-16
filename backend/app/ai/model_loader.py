"""
CROWDSHIELD MODEL INFERENCE LOADER & PREDICTION INTERFACE (PHASE 5B HARDENED)
=============================================================================
Provides clean loading of registered prototype models, schema validation,
and configurable temporal early-warning prediction interface.
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import xgboost as xgb

from app.ai.dataset.schema import CANDIDATE_MODEL_FEATURES, SAFE_BASELINES
from app.ai.dataset.schema_v2 import (
    CANDIDATE_TEMPORAL_FEATURES,
    PRIMARY_TEMPORAL_TARGET,
    TARGET_METADATA_V1,
    MODEL_TRAINING_THRESHOLD,
    DEFAULT_OPERATIONAL_ALERT_THRESHOLD,
)
from app.ai.training.model_registry import get_active_version_dir, RISK_MODEL_DIR
from app.ai.training.evaluator import generate_shap_explainability
from app.ai.services.early_warning_engine import EarlyWarningEngine, EarlyWarningState


_cached_model_data: Optional[Dict[str, Any]] = None


def load_registered_model(version_dir: Optional[str] = None, force_reload: bool = False) -> Optional[Dict[str, Any]]:
    """
    Locates, validates, and loads active model artifact package.
    """
    global _cached_model_data
    if _cached_model_data is not None and not force_reload:
        return _cached_model_data

    target_dir = version_dir or get_active_version_dir()
    if not target_dir or not os.path.exists(target_dir):
        return None

    model_json = os.path.join(target_dir, "model.json")
    model_pkl = os.path.join(target_dir, "model.pkl")
    meta_json = os.path.join(target_dir, "metadata.json")
    schema_json = os.path.join(target_dir, "feature_schema.json")
    calib_pkl = os.path.join(target_dir, "calibration.pkl")
    th_json = os.path.join(target_dir, "threshold.json")

    # Load Model
    model = None
    if os.path.exists(model_json):
        model = xgb.XGBClassifier()
        model.load_model(model_json)
    elif os.path.exists(model_pkl):
        model = joblib.load(model_pkl)
    else:
        return None

    # Load Schema
    feature_cols = CANDIDATE_TEMPORAL_FEATURES
    if os.path.exists(schema_json):
        with open(schema_json, "r", encoding="utf-8") as f:
            feature_cols = json.load(f).get("feature_cols", CANDIDATE_TEMPORAL_FEATURES)

    # Load Metadata
    metadata = {}
    if os.path.exists(meta_json):
        with open(meta_json, "r", encoding="utf-8") as f:
            metadata = json.load(f)

    # Load Model Training Threshold (Validation Tuned)
    training_threshold = MODEL_TRAINING_THRESHOLD
    if os.path.exists(th_json):
        with open(th_json, "r", encoding="utf-8") as f:
            training_threshold = float(json.load(f).get("threshold", MODEL_TRAINING_THRESHOLD))

    # Load Calibrator if present
    calibrator = None
    if os.path.exists(calib_pkl):
        try:
            calibrator = joblib.load(calib_pkl)
        except Exception:
            calibrator = None

    _cached_model_data = {
        "model": model,
        "calibrator": calibrator,
        "training_threshold": training_threshold,
        "feature_cols": feature_cols,
        "metadata": metadata,
        "version_dir": target_dir
    }
    return _cached_model_data


def validate_feature_vector(
    feature_dict: Dict[str, float],
    expected_cols: List[str]
) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
    """
    Validates feature dictionary against expected schema, order, and values.
    Returns (is_valid, error_message, numpy_array).
    """
    missing_cols = [col for col in expected_cols if col not in feature_dict]
    if missing_cols:
        return False, f"Missing required features: {missing_cols[:3]}", None

    vec = []
    for col in expected_cols:
        val = feature_dict[col]
        if val is None or np.isnan(val) or np.isinf(val):
            return False, f"Invalid value (NaN/Inf/None) for feature '{col}'", None
        vec.append(float(val))

    return True, None, np.array([vec])


def predict_risk_probability(feature_dict: Dict[str, float]) -> Dict[str, Any]:
    """
    Evaluates ML prototype probability for future high-risk transition.
    If model fails or missing, returns explicit AI_UNAVAILABLE status.
    """
    data = load_registered_model()
    if data is None or data.get("model") is None:
        return {
            "status": "AI_UNAVAILABLE",
            "message": "No trained prototype AI model artifact found in registry.",
            "probability_high_risk": None,
            "predicted_class": "UNKNOWN",
            "is_degraded": True
        }

    model = data["model"]
    calibrator = data["calibrator"]
    training_threshold = data["training_threshold"]
    feature_cols = data["feature_cols"]
    metadata = data["metadata"]

    # Validate Schema
    is_valid, err_msg, feature_matrix = validate_feature_vector(feature_dict, feature_cols)
    if not is_valid:
        return {
            "status": "AI_UNAVAILABLE",
            "message": f"Feature validation failed: {err_msg}",
            "probability_high_risk": None,
            "predicted_class": "UNKNOWN",
            "is_degraded": True
        }

    # Predict raw probability
    if hasattr(model, "predict_proba"):
        raw_prob = float(model.predict_proba(feature_matrix)[:, 1][0])
    else:
        raw_prob = float(model.predict(feature_matrix)[0])

    # Calibrate probability if calibrator exists
    if calibrator is not None:
        calib_prob = float(calibrator.predict_proba(np.array([[raw_prob]]))[:, 1][0])
    else:
        calib_prob = raw_prob

    prob = round(float(np.clip(calib_prob, 0.0, 1.0)), 4)
    predicted_class = "HIGH_RISK" if prob >= training_threshold else "NORMAL"

    explanation = {}
    if prob >= training_threshold:
        row_df = pd.DataFrame(feature_matrix, columns=feature_cols)
        explanation = generate_shap_explainability(model, row_df, row_df.iloc[0], feature_cols)

    return {
        "status": "SUCCESS",
        "model_version": metadata.get("model_version", "v2.0.0"),
        "target": metadata.get("target", PRIMARY_TEMPORAL_TARGET),
        "horizon_seconds": metadata.get("prediction_horizon_seconds", 300),
        "raw_probability": round(raw_prob, 4),
        "calibrated_probability": prob,
        "probability_high_risk": prob,
        "model_training_threshold": training_threshold,
        "predicted_class": predicted_class,
        "model_status": metadata.get("model_status", "PROTOTYPE"),
        "label_type": metadata.get("label_type", "PHYSICS_DEFINED_PROXY"),
        "is_degraded": False,
        "explainability": explanation
    }


def predict_temporal_early_warning(
    feature_dict: Dict[str, float],
    zone_id: str = "default",
    camera_id: str = "default",
    event_id: str = "default",
    current_rule_risk: Optional[float] = None,
    telemetry_timestamp: Optional[str] = None,
    operational_alert_threshold: float = DEFAULT_OPERATIONAL_ALERT_THRESHOLD,
    available_history_steps: Optional[int] = 30,
) -> Dict[str, Any]:
    """
    Phase 5B Hardened Temporal Early-Warning Inference Interface.

    Separates AI probability from operational alert state and applies EarlyWarningEngine policy.
    Exposes complete timestamp semantics, provenance metadata, and explicit prototype disclaimers.
    """
    now_str = datetime.now(timezone.utc).isoformat()
    telem_ts = telemetry_timestamp or now_str

    base_pred = predict_risk_probability(feature_dict)
    if base_pred.get("status") != "SUCCESS":
        return {
            "status": base_pred.get("status", "AI_UNAVAILABLE"),
            "prediction_status": "AI_UNAVAILABLE",
            "model_version": "v2.0.0",
            "target": PRIMARY_TEMPORAL_TARGET,
            "horizon_seconds": 300,
            "ai_escalation_probability": None,
            "current_rule_based_risk": current_rule_risk,
            "operational_warning_state": EarlyWarningState.DEGRADED,
            "camera_id": camera_id,
            "zone_id": zone_id,
            "event_id": event_id,
            "is_degraded": True,
            "disclaimer": "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.",
        }

    prob = base_pred["calibrated_probability"]
    engine = EarlyWarningEngine(
        watch_threshold=0.35,
        early_warning_threshold=operational_alert_threshold,
        high_risk_threshold=0.85,
        persistence_steps=3,
        hysteresis_margin=0.15,
        required_history_steps=30,
    )

    alert = engine.evaluate_probability(
        prob,
        zone_id=zone_id,
        camera_id=camera_id,
        event_id=event_id,
        timestamp=telem_ts,
        available_history_steps=available_history_steps,
    )

    return {
        "status": "SUCCESS",
        "prediction_status": "SUCCESS",
        "model_version": base_pred.get("model_version", "v2.0.0"),
        "target": base_pred.get("target", PRIMARY_TEMPORAL_TARGET),
        "target_metadata": TARGET_METADATA_V1,
        "horizon_seconds": base_pred.get("horizon_seconds", 300),
        "ai_escalation_probability": prob,
        "current_rule_based_risk": current_rule_risk,
        "model_training_threshold": base_pred.get("model_training_threshold", MODEL_TRAINING_THRESHOLD),
        "operational_alert_threshold": operational_alert_threshold,
        "operational_warning_state": alert["operational_warning_state"],
        "raw_candidate_state": alert["raw_candidate_state"],
        "history_ready": alert.get("history_ready", True),
        "data_quality": alert.get("data_quality", "GOOD"),
        "event_id": event_id,
        "camera_id": camera_id,
        "zone_id": zone_id,
        "telemetry_timestamp": telem_ts,
        "feature_window_end_timestamp": telem_ts,
        "prediction_timestamp": now_str,
        "warning_timestamp": alert.get("first_warning_timestamp"),
        "model_status": "PROTOTYPE",
        "label_type": "PHYSICS_DEFINED_PROXY",
        "ground_truth_status": "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
        "generalization_status": "INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION",
        "is_degraded": False,
        "disclaimer": "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.",
        "explainability": base_pred.get("explainability", {}),
    }
