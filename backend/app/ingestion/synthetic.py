"""
CROWDSHIELD SYNTHETIC INGESTION ADAPTER
=======================================
Adapts the synthetic sensor generator into the BaseSensorIngestion interface.
Acts as primary fallback when live RTSP/CCTV/GPS telemetry is unavailable.
"""

from typing import Dict, Any
from sqlalchemy.orm import Session

from app.ingestion.base import BaseSensorIngestion
from app.ai.features import simulate_sensor_reading


class SyntheticSensorIngestion(BaseSensorIngestion):
    """
    Synthetic Sensor Ingestion Adapter for fallback and offline development.
    """

    def get_zone_features(self, zone_id: Any, db: Session) -> Dict[str, Any]:
        features = simulate_sensor_reading(zone_id=zone_id, db=db)
        
        # Attach confidence and fallback metadata
        features["confidence_score"] = 0.85
        features["telemetry_source"] = "synthetic_fallback"
        features["is_degraded"] = False
        features["quality_breakdown"] = {
            "freshness_score": 1.0,
            "camera_uptime_score": 0.85,
            "gps_sample_score": 0.70,
            "feed_age_seconds": 0.0
        }
        return features
