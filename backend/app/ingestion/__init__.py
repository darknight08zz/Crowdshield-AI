"""
CROWDSHIELD INGESTION MODULE
"""
from app.ingestion.base import BaseSensorIngestion
from app.ingestion.synthetic import SyntheticSensorIngestion
from app.ingestion.hybrid_cctv_gps import HybridCCTVGPSIngestion
from app.ingestion.factory import get_ingestion_adapter
from app.ingestion.quality import evaluate_telemetry_quality

__all__ = [
    "BaseSensorIngestion",
    "SyntheticSensorIngestion",
    "HybridCCTVGPSIngestion",
    "get_ingestion_adapter",
    "evaluate_telemetry_quality"
]
