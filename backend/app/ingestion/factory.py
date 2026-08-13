"""
CROWDSHIELD INGESTION FACTORY
=============================
Instantiates the active ingestion adapter based on the SENSOR_MODE environment config.
Enables runtime switching and automatic fallback between live CCTV/GPS feeds and synthetic data.
"""

import os
from typing import Optional
from app.core.config import settings
from app.ingestion.base import BaseSensorIngestion
from app.ingestion.synthetic import SyntheticSensorIngestion
from app.ingestion.hybrid_cctv_gps import HybridCCTVGPSIngestion


_ingestion_instance: Optional[BaseSensorIngestion] = None


def get_ingestion_adapter(mode_override: Optional[str] = None) -> BaseSensorIngestion:
    """
    Returns singleton instance of the configured sensor ingestion adapter.
    Mode can be controlled via environment variable `SENSOR_MODE=synthetic|live`.
    """
    global _ingestion_instance
    active_mode = (mode_override or getattr(settings, "SENSOR_MODE", os.getenv("SENSOR_MODE", "synthetic"))).lower()

    if active_mode == "live":
        if not isinstance(_ingestion_instance, HybridCCTVGPSIngestion):
            _ingestion_instance = HybridCCTVGPSIngestion()
    else:
        if not isinstance(_ingestion_instance, SyntheticSensorIngestion):
            _ingestion_instance = SyntheticSensorIngestion()

    return _ingestion_instance
