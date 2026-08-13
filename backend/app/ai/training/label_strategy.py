"""
CROWDSHIELD DOMAIN-ENCODED WEAK LABELING & CLASS IMBALANCE STRATEGY
====================================================================
Translates academic crowd-dynamics research thresholds (Fruin / Helbing) and officer-verified
incidents into ground-truth risk scores and high-risk precursor labels.

Class Imbalance Problem Statement:
----------------------------------
Catastrophic crowd crush disasters are extremely rare events (positive class < 2%).
Relying solely on unweighted historical disaster logs leads to severe class imbalance,
causing models to achieve high accuracy by under-predicting dangerous states.
This module applies domain-encoded weak labeling and sample weighting to prioritize high Recall.
"""

import numpy as np
import pandas as pd
from typing import Tuple


def apply_domain_labeling_and_weights(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, np.ndarray]:
    """
    Computes:
    1. `y_current_risk`: Continuous ground-truth risk score (0 to 100).
    2. `y_precursor_binary`: Binary indicator (1 if dangerous precursor state, 0 otherwise).
    3. `sample_weights`: Inverse-class frequency weights to heavily penalize false negatives.
    """
    density = df["current_density"].values
    inflow = df["inflow_rate"].values
    outflow = df["outflow_rate"].values
    speed = df["avg_pedestrian_speed"].values
    conflict = df["direction_conflict_score"].values
    incidents = df["recent_incident_count_10min"].values
    reverse_flow = df["reverse_flow_ratio"].values
    blockage = df["blockage_score"].values

    # Net accumulation ratio
    flow_delta_ratio = np.clip((inflow - outflow) / np.maximum(outflow, 30.0), -1.0, 2.0)

    # 1. Physics-based Risk Formulation
    base_risk = (
        (density ** 2) * 42.0 +                      # Density non-linear impact
        np.maximum(0, 1.0 - speed) * 16.0 +          # Stagnation penalty
        np.maximum(0, flow_delta_ratio) * 16.0 +     # Ingress compression penalty
        conflict * 10.0 +                            # Turbulence penalty
        incidents * 6.0 +                            # Active incident weight
        reverse_flow * 10.0 +                        # Counter-flow penalty
        blockage * 10.0                              # Concentrated bottleneck penalty
    )
    current_risk = np.clip(base_risk + np.random.normal(0, 1.5, len(df)), 0.0, 100.0)

    # 2. Fruin / Helbing Weak Labeling Precursor Rule (Academic High-Risk Indicator)
    # High density (>0.70 / 3.5 peds/m²) AND low speed (<0.45 m/s) OR severe blockage (>0.60)
    academic_precursor_condition = (
        ((density > 0.70) & (speed < 0.45)) |
        ((blockage > 0.60) & (reverse_flow > 0.35)) |
        (incidents >= 2.0) |
        (current_risk >= 65.0)
    )

    y_precursor = academic_precursor_condition.astype(int)

    # 3. Class Imbalance Sample Weighting (SMOTE-like loss weighting)
    # Give high-risk samples 4x weight during model training to maximize Recall
    pos_count = np.sum(y_precursor)
    neg_count = len(y_precursor) - pos_count
    pos_weight = (neg_count / max(1, pos_count)) * 2.0

    sample_weights = np.where(y_precursor == 1, pos_weight, 1.0)

    # 4. Multi-Horizon Trajectory Target Labels (Addendum Prompt 4)
    momentum = (flow_delta_ratio * 10.0) + (incidents * 4.0)
    risk_2min = np.clip(current_risk + (momentum * 0.40), 0.0, 100.0)
    risk_5min = np.clip(current_risk + momentum, 0.0, 100.0)
    risk_10min = np.clip(current_risk + (momentum * 1.75), 0.0, 100.0)

    labels_df = pd.DataFrame({
        "current_risk": current_risk,
        "risk_2min": risk_2min,
        "risk_5min": risk_5min,
        "risk_10min": risk_10min,
        "is_high_risk": y_precursor
    })

    return labels_df, pd.Series(y_precursor, name="is_high_risk"), sample_weights
