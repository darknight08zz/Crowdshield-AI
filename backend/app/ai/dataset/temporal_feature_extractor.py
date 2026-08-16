"""
TEMPORAL FEATURE EXTRACTOR & TARGET DEFINITIONS (PHASE 5)
==========================================================
Implements temporal feature windowing, derivatives, acceleration calculation,
strict boundary protection (event/camera/zone), and Phase 5 candidate targets.
"""

from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
import numpy as np

from app.ai.dataset.schema import SAFE_BASELINES
from app.ai.dataset.schema_v2 import CANDIDATE_TEMPORAL_FEATURES


def compute_row_physics_risk(row: pd.Series) -> float:
    """Computes instantaneous physics risk score (0-100 scale)."""
    def _get_val(key: str, default: float) -> float:
        val = row.get(key)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return float(default)
        try:
            return float(val)
        except (ValueError, TypeError):
            return float(default)

    density = _get_val("density", SAFE_BASELINES["density"])
    speed = _get_val("average_speed", SAFE_BASELINES["average_speed"])
    inflow = _get_val("inflow_rate", SAFE_BASELINES["inflow_rate"])
    outflow = _get_val("outflow_rate", SAFE_BASELINES["outflow_rate"])
    conflict = _get_val("direction_conflict_score", SAFE_BASELINES["direction_conflict_score"])
    incidents = _get_val("recent_incident_count_10min", 0.0)
    reverse_flow = _get_val("reverse_flow_ratio", SAFE_BASELINES["reverse_flow_ratio"])
    blockage = _get_val("blockage_score", SAFE_BASELINES["blockage_score"])

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


def compute_phase5_targets(df: pd.DataFrame, horizon_steps: int = 30) -> pd.DataFrame:
    """
    Computes Phase 5 candidate targets looking ahead [t+1 to t+horizon_steps]
    within the same event_id, camera_id, and zone_id partition.

    Targets computed:
      - RISK_AT_5M: Continuous future risk at t+300s
      - RISK_DELTA_5M: Risk(t+300s) - Risk(t)
      - RISK_DELTA_5M_CLASS: 0 (NO_ESCALATION), 1 (MODERATE), 2 (STRONG)
      - EARLY_ESCALATION_5M: Binary dynamic deterioration indicator (1 or 0)
    """
    df = df.copy()
    if "physics_risk" not in df.columns:
        df["physics_risk"] = df.apply(compute_row_physics_risk, axis=1)

    n = len(df)
    risk_arr = df["physics_risk"].to_numpy(dtype=np.float64)
    dens_arr = df["density"].to_numpy(dtype=np.float64)
    speed_arr = df["average_speed"].to_numpy(dtype=np.float64)
    inflow_arr = df["inflow_rate"].to_numpy(dtype=np.float64)
    outflow_arr = df["outflow_rate"].to_numpy(dtype=np.float64)

    event_arr = df["event_id"].to_numpy() if "event_id" in df.columns else np.array(["default"] * n)
    cam_arr = df["camera_id"].to_numpy() if "camera_id" in df.columns else np.array(["default"] * n)
    zone_arr = df["zone_id"].to_numpy() if "zone_id" in df.columns else np.array(["default"] * n)

    risk_at_5m = np.full(n, np.nan, dtype=np.float64)
    risk_delta_5m = np.full(n, np.nan, dtype=np.float64)
    risk_delta_class = np.full(n, np.nan, dtype=np.float64)
    early_escalation = np.full(n, np.nan, dtype=np.float64)

    for i in range(n):
        if i + horizon_steps >= n:
            continue

        evt = event_arr[i]
        cam = cam_arr[i]
        zne = zone_arr[i]

        # Check if the end of horizon is within the exact same boundary partition
        if event_arr[i + horizon_steps] == evt and cam_arr[i + horizon_steps] == cam and zone_arr[i + horizon_steps] == zne:
            fut_risks = risk_arr[i + 1 : i + horizon_steps + 1]
            fut_densities = dens_arr[i + 1 : i + horizon_steps + 1]
            fut_speeds = speed_arr[i + 1 : i + horizon_steps + 1]
            fut_inflows = inflow_arr[i + 1 : i + horizon_steps + 1]
            fut_outflows = outflow_arr[i + 1 : i + horizon_steps + 1]

            target_risk_5m = fut_risks[-1]
            cur_risk = risk_arr[i]
            cur_dens = dens_arr[i]
            cur_speed = speed_arr[i]

            delta_5m = target_risk_5m - cur_risk

            risk_at_5m[i] = target_risk_5m
            risk_delta_5m[i] = delta_5m

            if delta_5m < 10.0:
                risk_delta_class[i] = 0.0
            elif delta_5m < 25.0:
                risk_delta_class[i] = 1.0
            else:
                risk_delta_class[i] = 2.0

            max_future_density_delta = np.max(fut_densities) - cur_dens
            min_future_speed_delta = np.min(fut_speeds) - cur_speed
            max_future_flow_imbalance = np.max(fut_inflows - fut_outflows)
            max_future_risk_delta = np.max(fut_risks) - cur_risk

            is_deteriorating = (
                (max_future_density_delta >= 0.20 and min_future_speed_delta <= -0.25 and max_future_flow_imbalance >= 20.0 and max_future_risk_delta >= 15.0)
                or (cur_risk < 50.0 and np.max(fut_risks) >= 75.0)
            )
            early_escalation[i] = 1.0 if is_deteriorating else 0.0

    df["RISK_AT_5M"] = risk_at_5m
    df["RISK_DELTA_5M"] = risk_delta_5m
    df["RISK_DELTA_5M_CLASS"] = risk_delta_class
    df["EARLY_ESCALATION_5M"] = early_escalation

    return df


def extract_temporal_derivatives_and_accelerations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes 1st and 2nd order temporal derivatives (rate and acceleration)
    enforcing boundary protection so deltas do not cross event/camera/zone boundaries.
    """
    df = df.copy()

    # Pre-allocate derivative and acceleration columns
    df["density_change"] = 0.0
    df["density_rate"] = 0.0
    df["density_acceleration"] = 0.0
    df["speed_change"] = 0.0
    df["speed_rate"] = 0.0
    df["speed_acceleration"] = 0.0

    # Group by boundary identifiers to calculate derivatives within partition
    group_cols = [col for col in ["event_id", "camera_id", "zone_id"] if col in df.columns]

    def _process_group(group: pd.DataFrame) -> pd.DataFrame:
        group = group.sort_values("timestamp")

        # 1st order derivatives (deltas)
        dens_diff = group["density"].diff().fillna(0.0)
        speed_diff = group["average_speed"].diff().fillna(0.0)

        group["density_change"] = dens_diff
        group["density_rate"] = dens_diff / 10.0  # 10s step
        group["speed_change"] = speed_diff
        group["speed_rate"] = speed_diff / 10.0

        # 2nd order derivatives (accelerations)
        group["density_acceleration"] = group["density_change"].diff().fillna(0.0) / 10.0
        group["speed_acceleration"] = group["speed_change"].diff().fillna(0.0) / 10.0

        # Rolling window features strictly <= t
        group["rolling_density_mean"] = group["density"].rolling(window=5, min_periods=1).mean()
        group["rolling_density_std"] = group["density"].rolling(window=5, min_periods=1).std().fillna(0.0)
        group["rolling_speed_mean"] = group["average_speed"].rolling(window=5, min_periods=1).mean()
        group["rolling_speed_std"] = group["average_speed"].rolling(window=5, min_periods=1).std().fillna(0.0)

        # Derived flows
        group["flow_imbalance"] = group["inflow_rate"] - group["outflow_rate"]
        group["net_accumulation"] = group["flow_imbalance"]

        group["inflow_change"] = group["inflow_rate"].diff().fillna(0.0)
        group["outflow_change"] = group["outflow_rate"].diff().fillna(0.0)

        return group

    if group_cols:
        try:
            df = df.groupby(group_cols, group_keys=False).apply(_process_group, include_groups=False)
        except TypeError:
            df = df.groupby(group_cols, group_keys=False).apply(_process_group)
    else:
        df = _process_group(df)

    return df.reset_index(drop=True)


def build_temporal_sequence_samples(
    df: pd.DataFrame,
    sequence_length: int = 30,
    feature_cols: List[str] = CANDIDATE_TEMPORAL_FEATURES,
    target_col: str = "EARLY_ESCALATION_5M",
) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """
    Builds 3D temporal sequence arrays (N_samples, sequence_length, N_features)
    and target vector (N_samples,) strictly preserving event/camera/zone boundary protection.
    """
    X_seq_list = []
    y_list = []
    meta_records = []

    group_cols = [col for col in ["event_id", "camera_id", "zone_id"] if col in df.columns]

    if group_cols:
        grouped = df.groupby(group_cols)
    else:
        grouped = [("single_group", df)]

    for group_key, group in grouped:
        group = group.sort_values("timestamp").reset_index(drop=True)
        n = len(group)

        for i in range(sequence_length - 1, n):
            target_val = group.at[i, target_col]
            if pd.isna(target_val):
                continue

            # Slice window strictly <= i (historical window)
            window_df = group.iloc[i - sequence_length + 1 : i + 1]

            # Verify boundary check (redundant sanity check)
            if len(window_df) == sequence_length:
                seq_matrix = window_df[feature_cols].to_numpy(dtype=np.float32)
                X_seq_list.append(seq_matrix)
                y_list.append(target_val)

                meta_records.append({
                    "timestamp": group.at[i, "timestamp"],
                    "camera_id": group.at[i, "camera_id"] if "camera_id" in group.columns else "default",
                    "zone_id": group.at[i, "zone_id"] if "zone_id" in group.columns else "default",
                    "event_id": group.at[i, "event_id"] if "event_id" in group.columns else "default",
                })

    if not X_seq_list:
        return np.empty((0, sequence_length, len(feature_cols))), np.empty((0,)), pd.DataFrame()

    X_seq = np.array(X_seq_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.float32)
    meta_df = pd.DataFrame(meta_records)

    return X_seq, y, meta_df
