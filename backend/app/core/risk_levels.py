"""
CROWDSHIELD STANDARDIZED RISK BUCKET TAXONOMY
==============================================
PROTOTYPE THRESHOLDS DISCLAIMER:
These risk score thresholds (0-24 LOW, 25-49 MODERATE, 50-74 HIGH, 75-100 CRITICAL)
are prototype operational boundaries for system demonstration and testing.
They are NOT clinically or safety-validated real-world physical crowd safety limits,
and MUST be formally reviewed, calibrated, and validated against empirical event
incident telemetry or domain-expert/safety authority input before being deployed
for real-world event operations.
"""

from enum import Enum
from typing import Dict, Any, Optional


class RiskBucket(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Numeric Threshold Boundaries (0-100 scale)
RISK_THRESHOLDS = {
    RiskBucket.LOW: (0.0, 24.99),
    RiskBucket.MODERATE: (25.0, 49.99),
    RiskBucket.HIGH: (50.0, 74.99),
    RiskBucket.CRITICAL: (75.0, 100.0),
}


# Standardized Palette across Web and Mobile
RISK_COLOR_PALETTE: Dict[RiskBucket, Dict[str, str]] = {
    RiskBucket.LOW: {
        "hex": "#10B981",       # Emerald Green
        "name": "Emerald Green",
        "web_bg": "bg-emerald-950/40",
        "web_border": "border-emerald-500/50",
        "web_text": "text-emerald-400",
        "web_badge": "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
        "mobile_bg": "#064e3b",
    },
    RiskBucket.MODERATE: {
        "hex": "#F59E0B",       # Amber Yellow
        "name": "Amber Yellow",
        "web_bg": "bg-amber-950/40",
        "web_border": "border-amber-500/50",
        "web_text": "text-amber-400",
        "web_badge": "bg-amber-500/20 text-amber-300 border-amber-500/30",
        "mobile_bg": "#78350f",
    },
    RiskBucket.HIGH: {
        "hex": "#F97316",       # Orange
        "name": "Orange",
        "web_bg": "bg-orange-950/40",
        "web_border": "border-orange-500/50",
        "web_text": "text-orange-400",
        "web_badge": "bg-orange-500/20 text-orange-300 border-orange-500/30",
        "mobile_bg": "#7c2d12",
    },
    RiskBucket.CRITICAL: {
        "hex": "#EF4444",       # Red
        "name": "Red",
        "web_bg": "bg-rose-950/50",
        "web_border": "border-rose-500/80",
        "web_text": "text-rose-400",
        "web_badge": "bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse",
        "mobile_bg": "#7f1d1d",
    },
}


def get_risk_bucket(score: float) -> RiskBucket:
    """
    Classifies a raw 0-100 risk score into the standardized RiskBucket taxonomy:
    - 0 – 24  : LOW
    - 25 – 49 : MODERATE
    - 50 – 74 : HIGH
    - 75 – 100: CRITICAL
    """
    score_val = float(score)
    if score_val < 25.0:
        return RiskBucket.LOW
    elif score_val < 50.0:
        return RiskBucket.MODERATE
    elif score_val < 75.0:
        return RiskBucket.HIGH
    else:
        return RiskBucket.CRITICAL


def evaluate_multi_horizon_risk(
    current_risk: float,
    risk_2min: Optional[float] = None,
    risk_5min: Optional[float] = None,
    risk_10min: Optional[float] = None
) -> Dict[str, Any]:
    """
    Evaluates multi-horizon trajectory interaction across forecast horizons (Current, +2m, +5m, +10m).
    
    Multi-Horizon Interaction Rule:
    If a zone is currently LOW or MODERATE, but escalates to HIGH or CRITICAL at a future horizon (+2m, +5m, +10m),
    returns an actionable trajectory warning (e.g. 'LOW -> CRITICAL (+5m)') to prevent operator alert lag.
    """
    curr_bucket = get_risk_bucket(current_risk)

    forecasts = [
        ("2min", risk_2min),
        ("5min", risk_5min),
        ("10min", risk_10min)
    ]

    max_forecast_score = current_risk
    max_forecast_horizon = "current"
    max_forecast_bucket = curr_bucket

    for horizon_label, val in forecasts:
        if val is not None:
            bucket = get_risk_bucket(val)
            if val > max_forecast_score:
                max_forecast_score = val
                max_forecast_horizon = horizon_label
                max_forecast_bucket = bucket

    bucket_order = [RiskBucket.LOW, RiskBucket.MODERATE, RiskBucket.HIGH, RiskBucket.CRITICAL]
    curr_idx = bucket_order.index(curr_bucket)
    max_idx = bucket_order.index(max_forecast_bucket)

    is_escalating = max_idx > curr_idx

    if is_escalating:
        trajectory_warning = f"CURRENTLY {curr_bucket.value}, ESCALATING TO {max_forecast_bucket.value} (+{max_forecast_horizon})"
        display_status = f"{curr_bucket.value} → {max_forecast_bucket.value} (+{max_forecast_horizon})"
        effective_bucket = max_forecast_bucket if (max_idx - curr_idx >= 2 or max_forecast_bucket == RiskBucket.CRITICAL) else curr_bucket
    else:
        trajectory_warning = f"{curr_bucket.value} (STABLE)"
        display_status = curr_bucket.value
        effective_bucket = curr_bucket

    return {
        "current_score": round(current_risk, 1),
        "current_bucket": curr_bucket.value,
        "max_forecast_score": round(max_forecast_score, 1),
        "max_forecast_horizon": max_forecast_horizon,
        "max_forecast_bucket": max_forecast_bucket.value,
        "is_escalating": is_escalating,
        "trajectory_warning": trajectory_warning,
        "display_status": display_status,
        "effective_bucket": effective_bucket.value,
        "palette": RISK_COLOR_PALETTE[curr_bucket],
        "effective_palette": RISK_COLOR_PALETTE[effective_bucket]
    }
