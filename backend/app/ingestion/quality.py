"""
CROWDSHIELD TELEMETRY DATA QUALITY & CONFIDENCE EVALUATOR
==========================================================
Evaluates freshness, uptime, and sample density of CCTV feeds and GPS pings
to produce a normalized confidence_score (0.0 to 1.0) and flag degraded states.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone


def evaluate_telemetry_quality(
    feed_age_seconds: float,
    active_cameras_ratio: float,
    gps_sample_count: int,
    expected_gps_floor: int = 10,
    max_acceptable_age_sec: float = 30.0
) -> Dict[str, Any]:
    """
    Calculates composite telemetry confidence_score and degraded status.

    Formula Weights:
    - Feed Freshness (40%): 1.0 if age <= 5s, decaying to 0.0 at max_acceptable_age_sec
    - Camera Uptime (40%): Ratio of operational cameras in zone (0.0 to 1.0)
    - GPS Sample Size (20%): min(1.0, active_gps_pings / expected_floor)
    """
    # 1. Freshness Score
    if feed_age_seconds <= 5.0:
        freshness_score = 1.0
    elif feed_age_seconds >= max_acceptable_age_sec:
        freshness_score = 0.0
    else:
        freshness_score = 1.0 - ((feed_age_seconds - 5.0) / (max_acceptable_age_sec - 5.0))

    # 2. Camera Uptime Score
    camera_score = max(0.0, min(1.0, active_cameras_ratio))

    # 3. GPS Sample Score
    gps_score = max(0.0, min(1.0, gps_sample_count / max(1, expected_gps_floor)))

    # Composite Weighted Confidence Score
    confidence_score = (0.40 * freshness_score) + (0.40 * camera_score) + (0.20 * gps_score)
    confidence_score = round(max(0.0, min(1.0, confidence_score)), 3)

    is_degraded = confidence_score < 0.50 or freshness_score < 0.20

    return {
        "confidence_score": confidence_score,
        "is_degraded": is_degraded,
        "quality_breakdown": {
            "freshness_score": round(freshness_score, 3),
            "camera_uptime_score": round(camera_score, 3),
            "gps_sample_score": round(gps_score, 3),
            "feed_age_seconds": round(feed_age_seconds, 1)
        }
    }
