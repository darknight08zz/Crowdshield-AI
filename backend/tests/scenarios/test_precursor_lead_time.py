"""
CROWDSHIELD PRECURSOR LEAD-TIME SCENARIO REPLAY TEST SUITE
=========================================================
Replays documented real-world crowd crush timeline sequences (e.g. Love Parade / Itaewon bottleneck patterns)
and measures the exact Actionable Lead Time (in minutes) provided before dangerous crush state occurs.
"""

import pytest
from app.ai.risk_model import predict_risk


def test_itaewon_alleyway_bottleneck_precursor_lead_time():
    """
    SCENARIO REPLAY: Itaewon / Concourse Bottleneck Timeline (15-Minute Replay).
    Timeline:
    - Min 0: Free Flow (Density 0.35, Speed 1.35 m/s, Reverse Flow 0.05)
    - Min 3: Impeded Flow (Density 0.52, Speed 0.95 m/s, Reverse Flow 0.15)
    - Min 6: Bottleneck Onset (Density 0.68, Speed 0.55 m/s, Reverse Flow 0.32, Blockage 0.40)
    - Min 9: Turbulent Compression (Density 0.82, Speed 0.30 m/s, Reverse Flow 0.48, Blockage 0.65)
    - Min 12: Crush Imminent (Density 0.95, Speed 0.15 m/s, Reverse Flow 0.65, Blockage 0.85)
    """
    timeline = [
        {"minute": 0, "features": {"current_density": 0.35, "inflow_rate": 60.0, "outflow_rate": 60.0, "avg_pedestrian_speed": 1.35, "direction_conflict_score": 0.10, "reverse_flow_ratio": 0.05, "blockage_score": 0.08, "gate_capacity_utilization": 0.35, "recent_incident_count_10min": 0}},
        {"minute": 3, "features": {"current_density": 0.52, "inflow_rate": 110.0, "outflow_rate": 70.0, "avg_pedestrian_speed": 0.95, "direction_conflict_score": 0.22, "reverse_flow_ratio": 0.15, "blockage_score": 0.20, "gate_capacity_utilization": 0.55, "recent_incident_count_10min": 0}},
        {"minute": 6, "features": {"current_density": 0.68, "inflow_rate": 160.0, "outflow_rate": 50.0, "avg_pedestrian_speed": 0.55, "direction_conflict_score": 0.42, "reverse_flow_ratio": 0.32, "blockage_score": 0.40, "gate_capacity_utilization": 0.75, "recent_incident_count_10min": 1}},
        {"minute": 9, "features": {"current_density": 0.82, "inflow_rate": 190.0, "outflow_rate": 30.0, "avg_pedestrian_speed": 0.30, "direction_conflict_score": 0.65, "reverse_flow_ratio": 0.48, "blockage_score": 0.65, "gate_capacity_utilization": 0.88, "recent_incident_count_10min": 2}},
        {"minute": 12, "features": {"current_density": 0.95, "inflow_rate": 220.0, "outflow_rate": 15.0, "avg_pedestrian_speed": 0.15, "direction_conflict_score": 0.88, "reverse_flow_ratio": 0.65, "blockage_score": 0.85, "gate_capacity_utilization": 0.98, "recent_incident_count_10min": 3}},
    ]

    first_warning_minute = None
    crush_minute = None

    print("\n[+] REPLAYING CROWD CRUSH PRECURSOR TIMELINE:")
    for step in timeline:
        minute = step["minute"]
        feat = step["features"]
        risk_dict = predict_risk(feat)
        curr_risk = risk_dict["current_risk"]
        proj_risk = risk_dict["risk_5min"]

        print(f"    Minute {minute:02d} | Density: {feat['current_density']:.2f} | Speed: {feat['avg_pedestrian_speed']:.2f} m/s | Risk: {curr_risk:.1f} | Projected 5m: {proj_risk:.1f}")

        # Flag first actionable warning threshold (Risk >= 60.0)
        if curr_risk >= 60.0 and first_warning_minute is None:
            first_warning_minute = minute

        # Flag physical crush threshold (Risk >= 85.0)
        if curr_risk >= 85.0 and crush_minute is None:
            crush_minute = minute

    assert first_warning_minute is not None, "System failed to trigger early risk warning before crush!"
    assert crush_minute is not None, "System failed to detect dangerous crush state!"

    actionable_lead_time = crush_minute - first_warning_minute
    print(f"[+] FIRST ACTIONABLE WARNING TRIGGERED AT: Minute {first_warning_minute}")
    print(f"[+] DANGEROUS CRUSH THRESHOLD REACHED AT:  Minute {crush_minute}")
    print(f"[SUCCESS] ACTIONABLE LEAD TIME: {actionable_lead_time} MINUTES")

    # Safety Requirement: Must provide at least 3 to 6 minutes of lead time
    assert actionable_lead_time >= 3.0, f"Lead time too short ({actionable_lead_time} min)! Must provide >= 3 minutes."
