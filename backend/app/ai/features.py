"""
CROWDSHIELD FEATURE EXTRACTION PIPELINE
======================================
Computes per-zone feature vectors from raw sensor, camera, gate, and incident telemetry.
"""

from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta
import random
from sqlalchemy.orm import Session

from app.models.zone import Zone
from app.models.gate import Gate
from app.models.incident import Incident

# Feature vector column definitions used across training, inference, and explainability
FEATURE_NAMES: List[str] = [
    "current_density",              # Occupancy density ratio (0.0 to 1.0)
    "inflow_rate",                 # Ingress velocity (pedestrians / min)
    "outflow_rate",                # Egress velocity (pedestrians / min)
    "avg_pedestrian_speed",        # Average movement velocity (meters / second)
    "direction_conflict_score",    # Counter-flow turbulence index (0.0 smooth to 1.0 chaotic)
    "gate_capacity_utilization",   # Effective gate load percentage (0.0 to 1.0)
    "recent_incident_count_10min", # Number of reported incidents in zone within last 10 minutes
    "reverse_flow_ratio",          # Share of movement going against designated flow direction (0.0 to 1.0)
    "blockage_score"               # Spatially-concentrated speed drop index (0.0 to 1.0)
]

# Baseline safe values for explainability and anomaly detection
SAFE_BASELINES: Dict[str, float] = {
    "current_density": 0.40,
    "inflow_rate": 80.0,
    "outflow_rate": 80.0,
    "avg_pedestrian_speed": 1.20,
    "direction_conflict_score": 0.15,
    "gate_capacity_utilization": 0.50,
    "recent_incident_count_10min": 0.0,
    "reverse_flow_ratio": 0.05,
    "blockage_score": 0.10
}


def is_valid_uuid(val: Any) -> bool:
    if not val:
        return False
    try:
        UUID(str(val))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def simulate_sensor_reading(zone_id: Any, db: Session) -> Dict[str, Any]:
    """
    SYNTHETIC SENSOR PLACEHOLDER:
    =============================
    Generates plausible real-time sensor & telemetry readings for a zone when live IoT / camera
    feeds are unavailable.

    !!! REPLACEMENT NOTICE FOR PRODUCTION DEPLOYMENT !!!
    ---------------------------------------------------
    Before deploying to a real event, replace the internal body of this function with an ingestion query
    fetching live camera optical flow counts, Bluetooth LE density scans, and gate sensors.
    DO NOT MODIFY the function signature or return dict structure so all downstream AI model code
    remains intact.
    """
    zone_str = str(zone_id)
    zone = db.query(Zone).filter(Zone.id == UUID(zone_str)).first() if (db and is_valid_uuid(zone_str)) else None
    if not zone:
        current_density = 0.50
    else:
        current_density = float(zone.current_density)

    # Calculate real incident count from DB for the last 10 minutes
    ten_mins_ago = datetime.utcnow() - timedelta(minutes=10)
    incident_count = db.query(Incident).filter(
        Incident.zone_id == UUID(zone_str),
        Incident.created_at >= ten_mins_ago
    ).count() if (db and is_valid_uuid(zone_str)) else 0

    # Query gate capacities for this zone
    gates = db.query(Gate).filter(Gate.zone_id == UUID(zone_str)).all() if (db and is_valid_uuid(zone_str)) else []
    total_capacity = sum([g.capacity_per_min for g in gates]) if gates else 300
    restricted_gates = len([g for g in gates if g.status in ["restricted", "closed"]])

    # Derive physical dynamics directly from zone database metrics
    inflow = round(current_density * 180.0, 1)
    outflow = round(max(10.0, (1.0 - current_density) * 120.0), 1)
    speed = round(max(0.20, 1.40 - (current_density * 1.1)), 2)
    direction_conflict = round(min(0.95, max(0.05, current_density * 0.8)), 3)
    reverse_flow_ratio = round(min(0.95, max(0.01, current_density * 0.6)), 3)
    blockage_score = round(min(0.95, max(0.05, current_density * 0.7)), 3)

    gate_utilization = min(1.0, (inflow / max(1, total_capacity)) + (0.15 * restricted_gates))

    return {
        "current_density": round(current_density, 3),
        "inflow_rate": round(inflow, 1),
        "outflow_rate": round(outflow, 1),
        "avg_pedestrian_speed": round(speed, 2),
        "direction_conflict_score": round(direction_conflict, 3),
        "gate_capacity_utilization": round(gate_utilization, 3),
        "recent_incident_count_10min": float(incident_count),
        "reverse_flow_ratio": round(reverse_flow_ratio, 3),
        "blockage_score": round(blockage_score, 3)
    }


def extract_zone_features(zone_id: Any, db: Session, include_metadata: bool = False) -> Dict[str, Any]:
    """
    Primary Feature Pipeline Entrypoint.
    Delegates to active Ingestion Adapter (Hybrid CCTV/GPS or Synthetic Fallback)
    and outputs validated numeric feature dict matching FEATURE_NAMES.
    """
    from app.ingestion.factory import get_ingestion_adapter
    adapter = get_ingestion_adapter()
    raw_data = adapter.get_zone_features(zone_id=zone_id, db=db)

    features = {feature: float(raw_data.get(feature, SAFE_BASELINES.get(feature, 0.0))) for feature in FEATURE_NAMES}

    if include_metadata:
        features["net_accumulation"] = round(features["inflow_rate"] - features["outflow_rate"], 1)
        features["confidence_score"] = float(raw_data.get("confidence_score", 0.85))
        features["telemetry_source"] = str(raw_data.get("telemetry_source", "synthetic_fallback"))
        features["is_degraded"] = bool(raw_data.get("is_degraded", False))

    return features

