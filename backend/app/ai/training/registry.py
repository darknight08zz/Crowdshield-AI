"""
CROWDSHIELD VERSIONED MODEL REGISTRY
===================================
Manages serialized AI model versions, active model pointers, and instant rollbacks.
Prevents accidental overwrites of operational model artifacts.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import xgboost as xgb

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
POINTER_FILE = os.path.join(MODEL_DIR, "current_model.txt")
LEGACY_DEFAULT_PATH = os.path.join(MODEL_DIR, "xgboost_risk_model.json")


def ensure_model_dir():
    os.makedirs(MODEL_DIR, exist_ok=True)


def get_active_model_path() -> str:
    """
    Returns the absolute path to the currently active model artifact.
    Falls back to legacy xgboost_risk_model.json if pointer is missing.
    """
    ensure_model_dir()
    if os.path.exists(POINTER_FILE):
        with open(POINTER_FILE, "r", encoding="utf-8") as f:
            active_name = f.read().strip()
            active_path = os.path.join(MODEL_DIR, active_name)
            if os.path.exists(active_path):
                return active_path
    return LEGACY_DEFAULT_PATH


def list_registered_models() -> List[Dict[str, Any]]:
    """
    Lists all model versions saved in the registry with their metadata.
    """
    ensure_model_dir()
    models_info = []
    active_path = get_active_model_path()

    for filename in sorted(os.listdir(MODEL_DIR), reverse=True):
        if filename.startswith("model_v") and filename.endswith(".json") and not filename.endswith("_meta.json"):
            meta_filename = filename.replace(".json", "_meta.json")
            meta_path = os.path.join(MODEL_DIR, meta_filename)
            meta_data = {}
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta_data = json.load(f)
                except Exception:
                    meta_data = {}

            full_path = os.path.join(MODEL_DIR, filename)
            models_info.append({
                "filename": filename,
                "path": full_path,
                "is_active": (full_path == active_path),
                "created_at": meta_data.get("created_at", "unknown"),
                "metrics": meta_data.get("metrics", {})
            })

    return models_info


def save_versioned_model(model: xgb.XGBRegressor, metrics: Dict[str, Any]) -> str:
    """
    Serializes model with a versioned timestamp, writes metadata, and updates current_model.txt pointer.
    """
    ensure_model_dir()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    version_name = f"model_v{timestamp}.json"
    meta_name = f"model_v{timestamp}_meta.json"

    version_path = os.path.join(MODEL_DIR, version_name)
    meta_path = os.path.join(MODEL_DIR, meta_name)

    # 1. Save model artifact
    model.save_model(version_path)
    # Also save to legacy location for backward compatibility
    model.save_model(LEGACY_DEFAULT_PATH)

    # 2. Save metadata JSON
    meta_content = {
        "version": version_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_content, f, indent=2)

    # 3. Update pointer
    with open(POINTER_FILE, "w", encoding="utf-8") as f:
        f.write(version_name)

    print(f"[REGISTRY] Registered new model version: {version_name}")
    return version_path


def rollback_model(target_version: Optional[str] = None) -> str:
    """
    Rolls back active model pointer to a specified target version or previous version.
    """
    models = list_registered_models()
    if not models:
        raise FileNotFoundError("No registered model versions found to roll back to.")

    if target_version:
        target = next((m for m in models if m["filename"] == target_version), None)
        if not target:
            raise ValueError(f"Version {target_version} not found in model registry.")
        selected = target
    else:
        # Pick the second most recent version if available
        if len(models) > 1:
            selected = models[1]
        else:
            selected = models[0]

    with open(POINTER_FILE, "w", encoding="utf-8") as f:
        f.write(selected["filename"])

    # Synchronize legacy file
    rollback_model_obj = xgb.XGBRegressor()
    rollback_model_obj.load_model(selected["path"])
    rollback_model_obj.save_model(LEGACY_DEFAULT_PATH)

    print(f"[REGISTRY ROLLBACK] Active model successfully reverted to: {selected['filename']}")
    return selected["path"]
