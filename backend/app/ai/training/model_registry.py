"""
CROWDSHIELD MODEL REGISTRY & ARTIFACT MANAGEMENT (PHASE 4 - PARTS U, V, W, AE)
=================================================================================
Manages saving, versioning, metadata logging, and tracking for prototype ML models.
Enforces explicit metadata tagging (PROTOTYPE status, PROXY label type, non-validated ground truth).
"""

import os
import json
import joblib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import xgboost as xgb

BASE_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
RISK_MODEL_DIR = os.path.join(BASE_MODEL_DIR, "risk")
ACTIVE_VERSION_FILE = os.path.join(RISK_MODEL_DIR, "active_version.txt")


def ensure_model_dirs():
    os.makedirs(RISK_MODEL_DIR, exist_ok=True)


def register_trained_model(
    model: Any,
    metadata: Dict[str, Any],
    feature_schema: List[str],
    evaluation: Dict[str, Any],
    threshold: float,
    calibrator: Optional[Any] = None,
    version_str: Optional[str] = None
) -> str:
    """
    Saves a versioned model artifact package under models/risk/<version>/ containing:
    - model.json / model.pkl
    - metadata.json
    - feature_schema.json
    - evaluation.json
    - calibration.pkl
    - threshold.json
    """
    ensure_model_dirs()

    if not version_str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        version_str = f"v1.0.0_{ts}"

    version_dir = os.path.join(RISK_MODEL_DIR, version_str)
    os.makedirs(version_dir, exist_ok=True)

    # 1. Save model artifact
    if isinstance(model, xgb.XGBClassifier):
        model_path = os.path.join(version_dir, "model.json")
        model.save_model(model_path)
    else:
        model_path = os.path.join(version_dir, "model.pkl")
        joblib.dump(model, model_path)

    # 2. Enforce explicit prototype honesty tags in metadata (Part AE)
    enforced_metadata = {
        **metadata,
        "model_version": version_str,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "model_status": "PROTOTYPE",
        "label_type": "PROXY",
        "ground_truth_status": "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
        "selected_threshold": threshold,
        "target": metadata.get("target", "HIGH_RISK_WITHIN_5M"),
        "prediction_horizon_seconds": metadata.get("prediction_horizon_seconds", 300)
    }

    with open(os.path.join(version_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(enforced_metadata, f, indent=2)

    # 3. Save feature schema
    with open(os.path.join(version_dir, "feature_schema.json"), "w", encoding="utf-8") as f:
        json.dump({"feature_cols": feature_schema}, f, indent=2)

    # 4. Save evaluation report
    with open(os.path.join(version_dir, "evaluation.json"), "w", encoding="utf-8") as f:
        json.dump(evaluation, f, indent=2)

    # 5. Save threshold
    with open(os.path.join(version_dir, "threshold.json"), "w", encoding="utf-8") as f:
        json.dump({"threshold": threshold}, f, indent=2)

    # 6. Save calibrator if present
    if calibrator is not None:
        joblib.dump(calibrator, os.path.join(version_dir, "calibration.pkl"))

    # Update active version pointer
    with open(ACTIVE_VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(version_str)

    print(f"[REGISTRY] Registered trained prototype model version: {version_str} at {version_dir}")
    return version_dir


def get_active_version_dir() -> Optional[str]:
    """Returns absolute path to currently registered active model directory."""
    if os.path.exists(ACTIVE_VERSION_FILE):
        with open(ACTIVE_VERSION_FILE, "r", encoding="utf-8") as f:
            v_str = f.read().strip()
            v_dir = os.path.join(RISK_MODEL_DIR, v_str)
            if os.path.exists(v_dir):
                return v_dir

    # Fallback to latest subdirectory
    if os.path.exists(RISK_MODEL_DIR):
        dirs = [
            os.path.join(RISK_MODEL_DIR, d) for d in os.listdir(RISK_MODEL_DIR)
            if os.path.isdir(os.path.join(RISK_MODEL_DIR, d)) and d != "__pycache__"
        ]
        if dirs:
            return sorted(dirs)[-1]

    return None


def list_registered_risk_models() -> List[Dict[str, Any]]:
    """Lists all registered risk model versions and their metadata."""
    ensure_model_dirs()
    results = []
    active_dir = get_active_version_dir()

    if not os.path.exists(RISK_MODEL_DIR):
        return []

    for item in sorted(os.listdir(RISK_MODEL_DIR)):
        item_path = os.path.join(RISK_MODEL_DIR, item)
        if os.path.isdir(item_path):
            meta_path = os.path.join(item_path, "metadata.json")
            meta = {}
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                except Exception:
                    pass

            results.append({
                "version": item,
                "path": item_path,
                "is_active": (item_path == active_dir),
                "status": meta.get("model_status", "PROTOTYPE"),
                "created_at": meta.get("saved_at", "unknown"),
                "metrics": meta.get("test_metrics", {})
            })

    return results
