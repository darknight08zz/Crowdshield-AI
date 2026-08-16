"""
CROWDSHIELD CV TELEMETRY METRICS & BEHAVIOR EXTRACTOR
=====================================================
Calculates canonical physical and spatial telemetry metrics from active pedestrian tracks:
- Density (calibrated persons/m² vs uncalibrated NORMALIZED_ESTIMATE)
- Calibrated Speed (m/s) & Median Speed
- Dominant Direction & Reverse Flow Ratio
- Direction Conflict Score (circular variance of direction angles)
- Stagnation Ratio & Blockage Score
- Deterministic Rule-Based Behavior Classification
"""

import math
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

from app.ingestion.cv.calibration import pixel_to_world, calculate_metric_speed


def calculate_density(
    person_count: int,
    zone_area_m2: float = 500.0,
    homography_matrix: Optional[List[List[float]]] = None,
    is_calibrated: bool = False
) -> Tuple[float, str, str]:
    """
    Calculates spatial density and returns (density, unit, calibration_status).
    """
    if is_calibrated and zone_area_m2 > 0:
        density = person_count / float(zone_area_m2)
        return round(density, 3), "persons_per_m2", "HOMOGRAPHY"
    else:
        # Uncalibrated fallback: estimate relative to nominal area
        area = max(100.0, zone_area_m2)
        density = person_count / float(area)
        return round(density, 3), "NORMALIZED_ESTIMATE", "UNCALIBRATED"


def calculate_speed_metrics(
    tracks: List[Dict[str, Any]],
    homography_matrix: Optional[List[List[float]]] = None,
    is_calibrated: bool = False,
    pixel_scale: float = 0.05
) -> Dict[str, Any]:
    """
    Computes average speed, median speed, moving/stationary track counts, and speed unit.
    """
    if not tracks:
        return {
            "average_speed": 0.0,
            "median_speed": 0.0,
            "moving_track_count": 0,
            "stationary_track_count": 0,
            "stationary_ratio": 0.0,
            "speed_unit": "m_s" if is_calibrated else "NORMALIZED_SPEED"
        }

    speeds = []
    stationary_count = 0
    moving_count = 0

    for trk in tracks:
        history = trk.get("history", [])
        if len(history) >= 2:
            sp = calculate_metric_speed(
                track_history=history,
                transform_matrix=homography_matrix if is_calibrated else None,
                pixel_scale=pixel_scale
            )
        else:
            # Fallback based on velocity
            vx, vy = trk.get("velocity", [0.0, 0.0])
            pixel_v = math.sqrt(vx ** 2 + vy ** 2)
            sp = round(min(5.0, pixel_v * pixel_scale), 2)

        speeds.append(sp)

        # Check if stationary
        stat_dur = trk.get("stationary_duration", 0.0)
        if sp < 0.25 or stat_dur >= 3.0:
            stationary_count += 1
        else:
            moving_count += 1

    avg_speed = round(float(np.mean(speeds)), 2)
    median_speed = round(float(np.median(speeds)), 2)
    stationary_ratio = round(stationary_count / float(max(1, len(tracks))), 3)

    return {
        "average_speed": avg_speed,
        "median_speed": median_speed,
        "moving_track_count": moving_count,
        "stationary_track_count": stationary_count,
        "stationary_ratio": stationary_ratio,
        "speed_unit": "m_s" if is_calibrated else "NORMALIZED_SPEED"
    }


def calculate_direction_and_conflict(tracks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates dominant movement direction, circular variance direction_conflict_score,
    and reverse_flow_ratio.
    """
    moving_tracks = [t for t in tracks if t.get("displacement", 0.0) > 10.0]

    if not moving_tracks:
        return {
            "dominant_direction_angle": 0.0,
            "direction_conflict_score": 0.0,
            "reverse_flow_count": 0,
            "reverse_flow_ratio": 0.0
        }

    angles_deg = [t.get("direction_angle", 0.0) for t in moving_tracks]
    angles_rad = [math.radians(a) for a in angles_deg]

    # Convert to unit vectors
    cos_sum = sum(math.cos(r) for r in angles_rad)
    sin_sum = sum(math.sin(r) for r in angles_rad)
    n = float(len(angles_rad))

    mean_cos = cos_sum / n
    mean_sin = sin_sum / n

    # Resultant vector length R (0.0 to 1.0)
    R = math.sqrt(mean_cos ** 2 + mean_sin ** 2)
    dominant_angle_rad = math.atan2(mean_sin, mean_cos)
    dominant_angle_deg = round((math.degrees(dominant_angle_rad) + 360.0) % 360.0, 1)

    # Angular variance (0.0 = uniform direction, 1.0 = maximum conflict)
    direction_conflict_score = round(min(1.0, max(0.0, 1.0 - R)), 3)

    # Identify reverse flow tracks (>120° deviation from dominant direction)
    reverse_count = 0
    for a_deg in angles_deg:
        diff = abs(a_deg - dominant_angle_deg)
        if diff > 180.0:
            diff = 360.0 - diff
        if diff >= 120.0:
            reverse_count += 1

    reverse_flow_ratio = round(reverse_count / float(n), 3)

    return {
        "dominant_direction_angle": dominant_angle_deg,
        "direction_conflict_score": direction_conflict_score,
        "reverse_flow_count": reverse_count,
        "reverse_flow_ratio": reverse_flow_ratio
    }


def calculate_blockage_score(
    density_peds_m2: float,
    median_speed: float,
    stationary_ratio: float,
    inflow_rate: float,
    outflow_rate: float
) -> float:
    """
    Calculates composite blockage score (0.0 to 1.0).
    High density + low speed + high stationary ratio + flow imbalance indicate physical bottleneck.
    """
    d_factor = min(1.0, density_peds_m2 / 4.0)
    speed_factor = max(0.0, 1.0 - (median_speed / 1.5))
    flow_imbalance = abs(inflow_rate - outflow_rate) / float(max(1.0, inflow_rate + outflow_rate))

    score = (0.35 * d_factor) + (0.30 * speed_factor) + (0.20 * stationary_ratio) + (0.15 * flow_imbalance)
    return round(min(1.0, max(0.0, score)), 3)


def classify_crowd_behavior(
    density_peds_m2: float,
    median_speed: float,
    stationary_ratio: float,
    reverse_flow_ratio: float,
    direction_conflict_score: float,
    blockage_score: float,
    inflow_rate: float,
    outflow_rate: float
) -> str:
    """
    Deterministic Rule-Based Crowd Behavior Classifier.

    Returns one of:
    - "SURGE"
    - "STAGNATION"
    - "BOTTLENECK"
    - "REVERSE_FLOW"
    - "DIRECTION_CONFLICT"
    - "NORMAL"
    """
    if inflow_rate >= 60.0 and inflow_rate > outflow_rate * 1.8:
        return "SURGE"

    if blockage_score >= 0.60 or (density_peds_m2 >= 2.5 and median_speed < 0.4):
        return "BOTTLENECK"

    if median_speed < 0.3 and stationary_ratio >= 0.40:
        return "STAGNATION"

    if reverse_flow_ratio >= 0.25:
        return "REVERSE_FLOW"

    if direction_conflict_score >= 0.50:
        return "DIRECTION_CONFLICT"

    return "NORMAL"
