"""
CROWDSHIELD CV DYNAMIC STRATEGY SELECTOR
========================================
Dynamically switches between 'detection_tracking' (YOLOv8 + ByteTrack) and 'density_estimation' (CSRNet)
per zone based on local density conditions and occlusion levels.

HYSTERESIS BUFFER TO PREVENT FLAPPING:
--------------------------------------
To prevent rapid oscillating switches ('flapping') when crowd density hovers around the threshold (2.5 peds/m2),
this selector requires 3 consecutive frames above or below the threshold before switching modes.

Every strategy transition is logged with timestamp, zone ID, and trigger metrics for auditability.
"""

import time
import logging
from typing import Dict, Any, Tuple
from app.core.config import settings

logger = logging.getLogger("crowdshield.cv.strategy")


class StrategySwitchLogger:
    """Audit logger for tracking strategy transitions per zone."""
    history = []

    @classmethod
    def log_switch(cls, zone_id: str, old_strategy: str, new_strategy: str, reason: str):
        event = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "zone_id": zone_id,
            "old_strategy": old_strategy,
            "new_strategy": new_strategy,
            "reason": reason
        }
        cls.history.append(event)
        logger.warning(
            f"🔄 [CV STRATEGY SWITCH] Zone [{zone_id}]: {old_strategy} ➔ {new_strategy} | Reason: {reason}"
        )


# Per-zone state tracker for hysteresis buffering
_zone_strategy_states: Dict[str, Dict[str, Any]] = {}


def select_detection_strategy(
    zone_id: str,
    recent_density_estimate: float,
    threshold: float = settings.CV_OCCLUSION_DENSITY_THRESHOLD
) -> Tuple[str, str]:
    """
    Selects the optimal CV strategy per zone with hysteresis protection.

    Args:
        zone_id: Unique identifier for the venue zone
        recent_density_estimate: Density in peds/m2
        threshold: Density threshold above which occlusion breaks bounding-box tracking

    Returns:
        Tuple[str, str]: (active_strategy, reason)
        active_strategy: "detection_tracking" | "density_estimation"
    """
    global _zone_strategy_states

    if zone_id not in _zone_strategy_states:
        _zone_strategy_states[zone_id] = {
            "current_strategy": "detection_tracking",
            "consecutive_above": 0,
            "consecutive_below": 0
        }

    state = _zone_strategy_states[zone_id]
    current = state["current_strategy"]

    HYSTERESIS_COUNT = 3  # Requires 3 consecutive frames to switch

    if recent_density_estimate >= threshold:
        state["consecutive_above"] += 1
        state["consecutive_below"] = 0

        if current == "detection_tracking" and state["consecutive_above"] >= HYSTERESIS_COUNT:
            new_strategy = "density_estimation"
            reason = f"High occlusion (density {recent_density_estimate:.2f} >= threshold {threshold:.2f} for {HYSTERESIS_COUNT} frames)"
            StrategySwitchLogger.log_switch(zone_id, current, new_strategy, reason)
            state["current_strategy"] = new_strategy
            return new_strategy, reason
    else:
        state["consecutive_below"] += 1
        state["consecutive_above"] = 0

        if current == "density_estimation" and state["consecutive_below"] >= HYSTERESIS_COUNT:
            new_strategy = "detection_tracking"
            reason = f"Density subsided ({recent_density_estimate:.2f} < threshold {threshold:.2f} for {HYSTERESIS_COUNT} frames)"
            StrategySwitchLogger.log_switch(zone_id, current, new_strategy, reason)
            state["current_strategy"] = new_strategy
            return new_strategy, reason

    return current, f"Maintaining strategy (Density: {recent_density_estimate:.2f} peds/m2)"
