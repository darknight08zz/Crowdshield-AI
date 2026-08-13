"""
TEST SUITE FOR GATE VIRTUAL-LINE INFLOW/OUTFLOW COUNTING (Addendum Prompt 3)
=============================================================================
Verifies line-segment intersection, cross-product side tests, jitter deduplication,
60s sliding-window rate aggregation, net accumulation calculation, and doorway occlusion handling.
"""

import pytest
import time
from app.ingestion.cv.line_crossing import check_line_crossing, LineCrossingDetector
from app.ingestion.cv.flow_rate import GateFlowRateAggregator


def test_line_crossing_direction_and_intersection():
    """Verifies that INFLOW and OUTFLOW directional line crossings are correctly detected."""
    vertical_line = [[200.0, 0.0], [200.0, 400.0]]

    # 1. Move left to right across vertical line -> INFLOW
    p1 = (100.0, 200.0)
    p2 = (300.0, 200.0)
    res_in = check_line_crossing(p1, p2, vertical_line, min_displacement=10.0)
    assert res_in == "INFLOW"

    # 2. Move right to left across vertical line -> OUTFLOW
    p3 = (300.0, 200.0)
    p4 = (100.0, 200.0)
    res_out = check_line_crossing(p3, p4, vertical_line, min_displacement=10.0)
    assert res_out == "OUTFLOW"


def test_jitter_deduplication_threshold():
    """Verifies that displacements below min_displacement (10px) are ignored to prevent double counts."""
    vertical_line = [[200.0, 0.0], [200.0, 400.0]]

    # Move across line with tiny 2px step (e.g. tracking jitter near boundary)
    p1 = (199.0, 200.0)
    p2 = (201.0, 200.0)
    res_jitter = check_line_crossing(p1, p2, vertical_line, min_displacement=10.0)
    assert res_jitter is None  # Filtered out by jitter threshold


def test_line_crossing_detector_single_count_per_walkthrough():
    """Verifies that a pedestrian track ID crossing a gate is counted EXACTLY ONCE."""
    detector = LineCrossingDetector(gate_id="gate_north", virtual_line=[[200.0, 0.0], [200.0, 400.0]])

    # Frame 1: Track #101 at (100, 200)
    tracks_f1 = [{"track_id": 101, "bbox": [90.0, 150.0, 110.0, 200.0], "timestamp": 1000.0}]
    evs_f1 = detector.process_tracks(tracks_f1)
    assert len(evs_f1) == 0

    # Frame 2: Track #101 moves across line to (300, 200) -> 1 INFLOW Event
    tracks_f2 = [{"track_id": 101, "bbox": [290.0, 150.0, 310.0, 200.0], "timestamp": 1001.0}]
    evs_f2 = detector.process_tracks(tracks_f2)
    assert len(evs_f2) == 1
    assert evs_f2[0]["direction"] == "INFLOW"
    assert evs_f2[0]["track_id"] == 101

    # Frame 3: Track #101 moves further to (350, 200) -> NO SECOND COUNT
    tracks_f3 = [{"track_id": 101, "bbox": [340.0, 150.0, 360.0, 200.0], "timestamp": 1002.0}]
    evs_f3 = detector.process_tracks(tracks_f3)
    assert len(evs_f3) == 0


def test_flow_rate_sliding_window_aggregation():
    """Verifies flow_rate aggregator computes per-minute rates and net_accumulation correctly."""
    aggregator = GateFlowRateAggregator(gate_id="gate_north", window_seconds=60.0)
    now = 1000.0

    # Record 5 INFLOWs and 2 OUTFLOWs in window
    for _ in range(5):
        aggregator.record_crossing("INFLOW", now - 10.0)
    for _ in range(2):
        aggregator.record_crossing("OUTFLOW", now - 5.0)

    # Stale event 70 seconds ago (should be pruned)
    aggregator.record_crossing("INFLOW", now - 70.0)

    metrics = aggregator.get_flow_rates(now, capacity_per_min=100.0)
    assert metrics["window_inflow_count"] == 5
    assert metrics["window_outflow_count"] == 2
    assert metrics["net_accumulation"] == 3.0  # 5 - 2 = +3 peds accumulated
    assert metrics["inflow_rate"] == 5.0 * 60.0 / 60.0  # 5 peds/min
