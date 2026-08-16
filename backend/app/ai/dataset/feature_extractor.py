"""
CROWDSHIELD TEMPORAL FEATURE EXTRACTOR & WINDOW GENERATOR
=========================================================
Extracts temporal window features and constructs non-leaking multi-horizon prediction targets.

CRITICAL DATA LEAKAGE PREVENTION:
--------------------------------
1. Feature windows at timestamp t MUST NOT consume any telemetry observed after t.
2. Target horizons (t + 1s to t + horizon) MUST NOT be included in input feature calculations.
"""

from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd


def compute_row_physics_risk(row: pd.Series) -> float:
    """
    Computes deterministic physics risk score for a single telemetry row.
    """
    density = float(row.get("density", row.get("current_density", 0.4)))
    speed = float(row.get("average_speed", row.get("avg_pedestrian_speed", 1.2)))
    inflow = float(row.get("inflow_rate", 80.0))
    outflow = float(row.get("outflow_rate", 80.0))
    conflict = float(row.get("direction_conflict_score", 0.15))
    incidents = float(row.get("recent_incident_count_10min", 0.0))
    reverse_flow = float(row.get("reverse_flow_ratio", 0.05))
    blockage = float(row.get("blockage_score", 0.10))

    flow_delta_ratio = np.clip((inflow - outflow) / max(outflow, 30.0), -1.0, 2.0)

    base_risk = (
        (density ** 2) * 42.0 +
        max(0.0, 1.0 - speed) * 16.0 +
        max(0.0, flow_delta_ratio) * 16.0 +
        conflict * 10.0 +
        incidents * 6.0 +
        reverse_flow * 10.0 +
        blockage * 10.0
    )
    return float(np.clip(base_risk, 0.0, 100.0))


def calculate_derived_temporal_features(
    window_df: pd.DataFrame,
    current_idx: int
) -> Dict[str, float]:
    """
    Given a chronologically sorted DataFrame `window_df` containing observations up to `current_idx` (inclusive),
    computes temporal derivatives and rolling statistics.

    STRICT GUARANTEE: Only rows from index 0 to `current_idx` (inclusive) are used.
    """
    sub_df = window_df.iloc[: current_idx + 1]
    curr_row = sub_df.iloc[-1]

    # Current raw values
    density = float(curr_row.get("density", curr_row.get("current_density", 0.0)))
    speed = float(curr_row.get("average_speed", curr_row.get("avg_pedestrian_speed", 1.2)))
    inflow = float(curr_row.get("inflow_rate", 0.0))
    outflow = float(curr_row.get("outflow_rate", 0.0))

    flow_imbalance = inflow - outflow
    net_accumulation = flow_imbalance

    # Compute temporal deltas if previous history exists in window
    if len(sub_df) > 1:
        prev_row = sub_df.iloc[-2]
        prev_density = float(prev_row.get("density", prev_row.get("current_density", 0.0)))
        prev_speed = float(prev_row.get("average_speed", prev_row.get("avg_pedestrian_speed", 1.2)))
        prev_inflow = float(prev_row.get("inflow_rate", 0.0))
        prev_outflow = float(prev_row.get("outflow_rate", 0.0))

        density_change = density - prev_density
        speed_change = speed - prev_speed
        inflow_change = inflow - prev_inflow
        outflow_change = outflow - prev_outflow
    else:
        density_change = 0.0
        speed_change = 0.0
        inflow_change = 0.0
        outflow_change = 0.0

    # Rolling window statistics (up to last 5 rows)
    roll_window = sub_df.tail(5)
    roll_densities = roll_window["density"].values if "density" in roll_window else roll_window["current_density"].values
    roll_speeds = roll_window["average_speed"].values if "average_speed" in roll_window else roll_window["avg_pedestrian_speed"].values

    rolling_density_mean = float(np.mean(roll_densities))
    rolling_density_std = float(np.std(roll_densities)) if len(roll_densities) > 1 else 0.0

    rolling_speed_mean = float(np.mean(roll_speeds))
    rolling_speed_std = float(np.std(roll_speeds)) if len(roll_speeds) > 1 else 0.0

    density_rate = density_change
    speed_rate = speed_change

    return {
        "flow_imbalance": round(flow_imbalance, 2),
        "net_accumulation": round(net_accumulation, 2),
        "density_change": round(density_change, 4),
        "density_rate": round(density_rate, 4),
        "speed_change": round(speed_change, 4),
        "speed_rate": round(speed_rate, 4),
        "inflow_change": round(inflow_change, 2),
        "outflow_change": round(outflow_change, 2),
        "rolling_density_mean": round(rolling_density_mean, 4),
        "rolling_density_std": round(rolling_density_std, 4),
        "rolling_speed_mean": round(rolling_speed_mean, 4),
        "rolling_speed_std": round(rolling_speed_std, 4),
    }


def compute_target_labels(
    df: pd.DataFrame,
    current_idx: int,
    sec_per_sample: float = 10.0,
    precomputed_risk_scores: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    Looks forward into future window [t + 1s to t + horizon] to evaluate if zone enters HIGH (>= 70.0) or CRITICAL (>= 85.0) state.
    """
    total_len = len(df)

    samples_2m = int(max(1, 120 // sec_per_sample))
    samples_5m = int(max(1, 300 // sec_per_sample))
    samples_10m = int(max(1, 600 // sec_per_sample))

    idx_start = current_idx + 1
    if precomputed_risk_scores is not None and len(precomputed_risk_scores) == total_len:
        fut_2m_max = float(np.max(precomputed_risk_scores[idx_start : min(total_len, idx_start + samples_2m)])) if idx_start < total_len else 0.0
        fut_5m_max = float(np.max(precomputed_risk_scores[idx_start : min(total_len, idx_start + samples_5m)])) if idx_start < total_len else 0.0
        fut_10m_max = float(np.max(precomputed_risk_scores[idx_start : min(total_len, idx_start + samples_10m)])) if idx_start < total_len else 0.0
    else:
        fut_2m = df.iloc[idx_start : min(total_len, idx_start + samples_2m)]
        fut_5m = df.iloc[idx_start : min(total_len, idx_start + samples_5m)]
        fut_10m = df.iloc[idx_start : min(total_len, idx_start + samples_10m)]

        fut_2m_max = max([compute_row_physics_risk(r) for _, r in fut_2m.iterrows()]) if len(fut_2m) > 0 else 0.0
        fut_5m_max = max([compute_row_physics_risk(r) for _, r in fut_5m.iterrows()]) if len(fut_5m) > 0 else 0.0
        fut_10m_max = max([compute_row_physics_risk(r) for _, r in fut_10m.iterrows()]) if len(fut_10m) > 0 else 0.0

    # Threshold for High/Critical risk transition is >= 70.0
    h_2m = 1 if fut_2m_max >= 70.0 else 0
    h_5m = 1 if fut_5m_max >= 70.0 else 0
    h_10m = 1 if fut_10m_max >= 70.0 else 0
    proxy_target = h_5m

    return {
        "HIGH_RISK_WITHIN_2M": h_2m,
        "HIGH_RISK_WITHIN_5M": h_5m,
        "HIGH_RISK_WITHIN_10M": h_10m,
        "HIGH_RISK_STATE_TRANSITION_PROXY": proxy_target,
        "label_type": "PROXY",
        "ground_truth_status": "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
    }
