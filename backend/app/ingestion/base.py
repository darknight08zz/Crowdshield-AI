"""
CROWDSHIELD INGESTION BASE ADAPTER INTERFACE
============================================
Abstract interface for zone feature vector ingestion sources.
Allows seamless switching between synthetic simulation and live CCTV/GPS sensor feeds.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from sqlalchemy.orm import Session


class BaseSensorIngestion(ABC):
    """
    Abstract Base Class defining the contract for all CrowdShield sensor ingestion adapters.
    All adapters must return a dictionary containing the exact feature vector expected
    by the AI engine, plus confidence and data-quality metadata.
    """

    @abstractmethod
    def get_zone_features(self, zone_id: Any, db: Session) -> Dict[str, Any]:
        """
        Retrieves feature vector for a specific zone.

        Must return a dict containing:
        - current_density (float: 0.0 to 1.0)
        - inflow_rate (float: peds / min)
        - outflow_rate (float: peds / min)
        - avg_pedestrian_speed (float: m/s)
        - direction_conflict_score (float: 0.0 to 1.0)
        - gate_capacity_utilization (float: 0.0 to 1.0)
        - recent_incident_count_10min (float)
        - reverse_flow_ratio (float: 0.0 to 1.0)
        - blockage_score (float: 0.0 to 1.0)
        - confidence_score (float: 0.0 to 1.0)
        - telemetry_source (str: "synthetic" | "live_cctv_gps" | "hybrid")
        - is_degraded (bool)
        """
        pass
