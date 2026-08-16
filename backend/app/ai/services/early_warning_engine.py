"""
EARLY WARNING DECISION ENGINE & ALERT STABILITY (PHASE 5B HARDENED)
===================================================================
Implements operational alert policy logic, deterministic state transitions:
(WARMING_UP, DEGRADED, NORMAL, WATCH, EARLY_WARNING, HIGH_RISK),
n-step persistence, hysteresis thresholding, and alert stabilization.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class EarlyWarningState:
    WARMING_UP = "WARMING_UP"
    DEGRADED = "DEGRADED"
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    EARLY_WARNING = "EARLY_WARNING"
    HIGH_RISK = "HIGH_RISK"


class EarlyWarningEngine:
    """
    Operational Alert Stability Engine.
    Separates raw AI model escalation probability from operational alert decision state.
    """
    def __init__(
        self,
        watch_threshold: float = 0.35,
        early_warning_threshold: float = 0.50,
        high_risk_threshold: float = 0.85,
        persistence_steps: int = 3,
        hysteresis_margin: float = 0.15,
        min_alert_hold_steps: int = 3,
        required_history_steps: int = 30,
    ):
        self.watch_threshold = watch_threshold
        self.early_warning_threshold = early_warning_threshold
        self.high_risk_threshold = high_risk_threshold
        self.persistence_steps = persistence_steps
        self.hysteresis_margin = hysteresis_margin
        self.min_alert_hold_steps = min_alert_hold_steps
        self.required_history_steps = required_history_steps

        # State tracking per zone/camera
        self._zone_states: Dict[str, Dict[str, Any]] = {}

    def _get_zone_tracker(self, key: str) -> Dict[str, Any]:
        if key not in self._zone_states:
            self._zone_states[key] = {
                "current_state": EarlyWarningState.NORMAL,
                "consecutive_high_reads": 0,
                "steps_in_current_state": 0,
                "last_probability": 0.0,
                "history": [],
                "first_warning_timestamp": None,
            }
        return self._zone_states[key]

    def evaluate_probability(
        self,
        probability: Optional[float],
        zone_id: str = "default",
        camera_id: str = "default",
        event_id: str = "default",
        timestamp: Optional[str] = None,
        is_degraded: bool = False,
        available_history_steps: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates temporal prediction probability and applies persistence + hysteresis
        to return a stable operational alert state.

        Deterministically handles WARMING_UP and DEGRADED states.
        """
        key = f"{event_id}_{camera_id}_{zone_id}"
        tracker = self._get_zone_tracker(key)

        now_str = timestamp or datetime.now(timezone.utc).isoformat()

        # Handle Degraded / Missing Telemetry
        if is_degraded or probability is None:
            return {
                "event_id": event_id,
                "camera_id": camera_id,
                "zone_id": zone_id,
                "timestamp": now_str,
                "probability": None,
                "history_ready": False,
                "data_quality": "DEGRADED",
                "raw_candidate_state": EarlyWarningState.DEGRADED,
                "operational_warning_state": EarlyWarningState.DEGRADED,
                "state_changed": (tracker["current_state"] != EarlyWarningState.DEGRADED),
                "consecutive_high_reads": 0,
                "steps_in_state": tracker["steps_in_current_state"],
                "first_warning_timestamp": tracker["first_warning_timestamp"],
            }

        tracker["history"].append(probability)
        if len(tracker["history"]) > 60:
            tracker["history"].pop(0)

        history_count = available_history_steps if available_history_steps is not None else len(tracker["history"])

        # Handle Warm-up Behavior
        if history_count < self.required_history_steps:
            return {
                "event_id": event_id,
                "camera_id": camera_id,
                "zone_id": zone_id,
                "timestamp": now_str,
                "probability": round(float(probability), 4),
                "history_ready": False,
                "data_quality": "WARMING_UP",
                "raw_candidate_state": EarlyWarningState.WARMING_UP,
                "operational_warning_state": EarlyWarningState.WARMING_UP,
                "state_changed": (tracker["current_state"] != EarlyWarningState.WARMING_UP),
                "consecutive_high_reads": 0,
                "steps_in_state": tracker["steps_in_current_state"],
                "first_warning_timestamp": None,
            }

        tracker["steps_in_current_state"] += 1
        tracker["last_probability"] = probability

        prev_state = tracker["current_state"]
        new_state = prev_state

        # Determine raw candidate state
        if probability >= self.high_risk_threshold:
            raw_candidate = EarlyWarningState.HIGH_RISK
        elif probability >= self.early_warning_threshold:
            raw_candidate = EarlyWarningState.EARLY_WARNING
        elif probability >= self.watch_threshold:
            raw_candidate = EarlyWarningState.WATCH
        else:
            raw_candidate = EarlyWarningState.NORMAL

        # Strict Persistence: Consecutive qualifying reads required
        if probability >= self.early_warning_threshold:
            tracker["consecutive_high_reads"] += 1
        else:
            # RESET immediately on non-qualifying read (Intermittent HIGH, NORMAL, HIGH will NOT trigger persistence)
            tracker["consecutive_high_reads"] = 0

        # Escalation Logic (Requires persistence_steps for EARLY_WARNING / HIGH_RISK)
        if tracker["consecutive_high_reads"] >= self.persistence_steps:
            if probability >= self.high_risk_threshold:
                new_state = EarlyWarningState.HIGH_RISK
            elif prev_state == EarlyWarningState.HIGH_RISK and probability >= (self.high_risk_threshold - self.hysteresis_margin):
                new_state = EarlyWarningState.HIGH_RISK
            else:
                new_state = EarlyWarningState.EARLY_WARNING
        elif raw_candidate in [EarlyWarningState.WATCH, EarlyWarningState.EARLY_WARNING, EarlyWarningState.HIGH_RISK]:
            if prev_state in [EarlyWarningState.NORMAL, EarlyWarningState.WARMING_UP]:
                new_state = EarlyWarningState.WATCH

        # De-escalation Logic with Hysteresis (Requires dropping below threshold - margin)
        if prev_state == EarlyWarningState.HIGH_RISK:
            if probability < (self.high_risk_threshold - self.hysteresis_margin):
                if tracker["steps_in_current_state"] >= self.min_alert_hold_steps:
                    new_state = EarlyWarningState.EARLY_WARNING
        elif prev_state == EarlyWarningState.EARLY_WARNING:
            if probability < (self.early_warning_threshold - self.hysteresis_margin):
                if tracker["steps_in_current_state"] >= self.min_alert_hold_steps:
                    new_state = EarlyWarningState.WATCH
        elif prev_state == EarlyWarningState.WATCH:
            if probability < (self.watch_threshold - self.hysteresis_margin):
                new_state = EarlyWarningState.NORMAL

        # Track first timestamp of actual warning emission for lead time audit
        if new_state in [EarlyWarningState.EARLY_WARNING, EarlyWarningState.HIGH_RISK] and tracker["first_warning_timestamp"] is None:
            tracker["first_warning_timestamp"] = now_str
        elif new_state == EarlyWarningState.NORMAL:
            tracker["first_warning_timestamp"] = None

        if new_state != prev_state:
            tracker["current_state"] = new_state
            tracker["steps_in_current_state"] = 0

        return {
            "event_id": event_id,
            "camera_id": camera_id,
            "zone_id": zone_id,
            "timestamp": now_str,
            "probability": round(float(probability), 4),
            "history_ready": True,
            "data_quality": "GOOD",
            "raw_candidate_state": raw_candidate,
            "operational_warning_state": new_state,
            "state_changed": (new_state != prev_state),
            "consecutive_high_reads": tracker["consecutive_high_reads"],
            "steps_in_state": tracker["steps_in_current_state"],
            "first_warning_timestamp": tracker["first_warning_timestamp"],
        }
