"""
CROWDSHIELD ROLLING-WINDOW FLOW RATE AGGREGATOR
================================================
Aggregates raw line-crossing timestamps into rate-per-minute telemetry metrics
expected by the AI feature extraction pipeline.

Calculates:
-----------
1. inflow_peds_min: Rolling 60s inflow rate extrapolated to per-minute
2. outflow_peds_min: Rolling 60s outflow rate extrapolated to per-minute
3. net_accumulation: (inflow_count - outflow_count) in window (critical predictive signal)
4. gate_capacity_utilization: inflow_peds_min / capacity_per_min
"""

import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("crowdshield.cv.flow_rate")


class GateFlowRateAggregator:
    """
    Maintains sliding window buffers of line-crossing timestamps for a gate.
    """

    def __init__(self, gate_id: str, window_seconds: float = 60.0):
        self.gate_id = gate_id
        self.window_seconds = window_seconds

        self.inflow_timestamps: List[float] = []
        self.outflow_timestamps: List[float] = []

    def record_crossing(self, direction: str, timestamp: float):
        """
        Appends a verified crossing event timestamp.
        """
        if direction == "INFLOW":
            self.inflow_timestamps.append(timestamp)
        elif direction == "OUTFLOW":
            self.outflow_timestamps.append(timestamp)

    def get_flow_rates(self, now: float, capacity_per_min: float = 100.0) -> Dict[str, float]:
        """
        Prunes timestamps outside sliding window and calculates per-minute rate metrics.
        """
        cutoff = now - self.window_seconds

        # Prune stale timestamps
        self.inflow_timestamps = [t for t in self.inflow_timestamps if t >= cutoff]
        self.outflow_timestamps = [t for t in self.outflow_timestamps if t >= cutoff]

        inflow_count = len(self.inflow_timestamps)
        outflow_count = len(self.outflow_timestamps)

        # Extrapolate to per-minute rates
        scale_factor = 60.0 / max(1.0, self.window_seconds)
        inflow_rate = round(inflow_count * scale_factor, 1)
        outflow_rate = round(outflow_count * scale_factor, 1)

        net_accumulation = float(inflow_count - outflow_count)
        gate_utilization = min(1.0, round(inflow_rate / max(1.0, capacity_per_min), 3))

        return {
            "gate_id": self.gate_id,
            "inflow_rate": inflow_rate,
            "outflow_rate": outflow_rate,
            "net_accumulation": net_accumulation,
            "gate_capacity_utilization": gate_utilization,
            "window_inflow_count": inflow_count,
            "window_outflow_count": outflow_count
        }
