"""
CROWDSHIELD REALTIME INFERENCE RESULT STORE (PHASE 6B)
======================================================
Thread-safe, in-memory bounded store for the latest RealtimeInferenceResult per stream.

Key design decisions:
- Keyed strictly by (event_id, camera_id, zone_id) tuple.
  Camera A never overwrites Camera B; Zone A never overwrites Zone B;
  Event A never contaminates Event B.
- Stale detection: if the wall-clock age of the latest result exceeds
  stale_threshold_seconds, the returned record is augmented with:
    is_stale       = True
    camera_health_status = "OFFLINE"  (preserved for backward compat)
    is_degraded    = True
    operational_warning_state = "DEGRADED"
  The raw stored record is NOT mutated — only the returned copy is.
- No historical storage — only the latest result per key is retained.
- stale_threshold_seconds defaults to 15.0 s and is configurable.

Structured log events:
  INFERENCE_RESULT_STORED, STREAM_STALE, AI_UNAVAILABLE, CAMERA_OFFLINE
"""

import time
import logging
import threading
from typing import Dict, List, Any, Optional, Tuple

from app.schemas.realtime_inference import RealtimeInferenceResponse

logger = logging.getLogger("crowdshield.realtime.store")

# Default stale threshold (seconds).  Override in tests or via configuration.
DEFAULT_STALE_THRESHOLD_SECONDS: float = 15.0


class RealtimeInferenceResultStore:
    """
    Thread-safe latest inference result repository keyed by (event_id, camera_id, zone_id).
    """

    def __init__(self, stale_threshold_seconds: float = DEFAULT_STALE_THRESHOLD_SECONDS):
        self._lock = threading.Lock()
        # raw validated dict per stream key
        self._store: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        # wall-clock timestamp of last update per key
        self._last_update_ts: Dict[Tuple[str, str, str], float] = {}
        self.stale_threshold_seconds = stale_threshold_seconds

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def update_result(self, result_payload: Dict[str, Any]) -> RealtimeInferenceResponse:
        """
        Validates and stores the latest inference result for a stream.

        Parameters
        ----------
        result_payload : Dict[str, Any]
            Raw RealtimeInferenceResult dict produced by Phase 6A orchestrator.

        Returns
        -------
        RealtimeInferenceResponse
            The validated Pydantic model for the caller's convenience.
        """
        event_id = str(result_payload.get("event_id", "evt_01"))
        camera_id = str(result_payload.get("camera_id", ""))
        zone_id = str(result_payload.get("zone_id", ""))
        key = (event_id, camera_id, zone_id)

        response_model = RealtimeInferenceResponse.from_orchestrator_result(result_payload)
        response_dict = response_model.model_dump()

        with self._lock:
            self._store[key] = response_dict
            self._last_update_ts[key] = time.monotonic()

        logger.debug(
            "[RESULT STORE] INFERENCE_RESULT_STORED: key=%s ai_status=%s",
            key,
            response_dict.get("ai_status"),
        )
        return response_model

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_latest_result(
        self,
        camera_id: str,
        zone_id: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Returns the latest inference result for the specified camera/zone/event.

        Stale detection
        ---------------
        If the result is older than stale_threshold_seconds the returned copy is
        augmented with staleness indicators WITHOUT modifying the stored record:

          is_stale                  = True
          camera_health_status      = "OFFLINE"
          is_degraded               = True
          operational_warning_state = "DEGRADED"
          ai_status                 = "STALE"

        Returns None if no matching result exists.
        """
        now = time.monotonic()

        with self._lock:
            for (e_id, c_id, z_id), res in self._store.items():
                if c_id != camera_id:
                    continue
                if zone_id and z_id != zone_id:
                    continue
                if event_id and e_id != event_id:
                    continue

                key = (e_id, c_id, z_id)
                elapsed = now - self._last_update_ts.get(key, 0.0)
                res_copy = dict(res)

                if elapsed > self.stale_threshold_seconds:
                    res_copy["is_stale"] = True
                    res_copy["camera_health_status"] = "OFFLINE"
                    res_copy["is_degraded"] = True
                    res_copy["operational_warning_state"] = "DEGRADED"
                    res_copy["ai_status"] = "STALE"
                    logger.debug(
                        "[RESULT STORE] STREAM_STALE: key=%s elapsed=%.1fs", key, elapsed
                    )
                else:
                    res_copy["is_stale"] = False

                return res_copy

        return None

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def list_active_streams(self) -> List[Dict[str, Any]]:
        """Returns freshness status for all tracked streams."""
        out = []
        now = time.monotonic()
        with self._lock:
            for (e_id, c_id, z_id), last_ts in self._last_update_ts.items():
                elapsed = now - last_ts
                out.append(
                    {
                        "event_id": e_id,
                        "camera_id": c_id,
                        "zone_id": z_id,
                        "seconds_since_last_update": round(elapsed, 2),
                        "is_stale": elapsed > self.stale_threshold_seconds,
                    }
                )
        return out

    def clear_stream(self, event_id: str, camera_id: str, zone_id: str) -> bool:
        """Removes a specific stream entry. Returns True if it existed."""
        key = (event_id, camera_id, zone_id)
        with self._lock:
            removed = self._store.pop(key, None) is not None
            self._last_update_ts.pop(key, None)
        return removed

    def clear_all(self) -> None:
        """Flushes the entire store. Intended for test tearDown."""
        with self._lock:
            self._store.clear()
            self._last_update_ts.clear()


# ---------------------------------------------------------------------------
# Application-wide singleton
# ---------------------------------------------------------------------------

inference_result_store = RealtimeInferenceResultStore()
