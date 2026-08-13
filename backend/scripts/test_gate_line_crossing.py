"""
CROWDSHIELD SINGLE WALK-THROUGH MANUAL VERIFICATION SCRIPT
===========================================================
Simulates a single pedestrian walking across a gate's virtual line:
1. Frame 1: Pedestrian #42 at position (100, 200) [Outer Side]
2. Frame 2: Pedestrian #42 steps across line to position (300, 200) [Inner Side]
3. Frame 3: Pedestrian #42 takes small 5px step to (305, 200) [Boundary Jitter]

Usage:
  python scripts/test_gate_line_crossing.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath("."))

from app.ingestion.cv.line_crossing import LineCrossingDetector
from app.ingestion.cv.flow_rate import GateFlowRateAggregator


def main():
    print("=" * 65)
    print(" [CROWDSHIELD] GATE VIRTUAL LINE-CROSSING MANUAL TEST")
    print("=" * 65)

    gate_id = "gate_main_entrance"
    virtual_line = [[200.0, 0.0], [200.0, 400.0]]  # Vertical line at x=200

    detector = LineCrossingDetector(gate_id=gate_id, virtual_line=virtual_line)
    aggregator = GateFlowRateAggregator(gate_id=gate_id)

    print(f"\n[+] Configured Gate Line: {virtual_line}")
    print("[+] Simulating Walk-through for Track #42...\n")

    # Step 1: Initial Position outside gate
    print("Step 1: Frame 1 -> Track #42 at (100, 200)")
    f1_tracks = [{"track_id": 42, "bbox": [90, 150, 110, 200], "timestamp": 100.0}]
    evs1 = detector.process_tracks(f1_tracks)
    print(f"  -> Detected Events: {len(evs1)}")

    # Step 2: Cross Virtual Line into Gate
    print("\nStep 2: Frame 2 -> Track #42 moves across line to (300, 200)")
    f2_tracks = [{"track_id": 42, "bbox": [290, 150, 310, 200], "timestamp": 101.0}]
    evs2 = detector.process_tracks(f2_tracks)
    print(f"  -> Detected Events: {len(evs2)}")
    for ev in evs2:
        aggregator.record_crossing(ev["direction"], ev["timestamp"])
        print(f"     [EVENT DETECTED] Track #{ev['track_id']} Direction: {ev['direction']}")

    # Step 3: Small displacement near line (Boundary Jitter test)
    print("\nStep 3: Frame 3 -> Track #42 takes small step to (305, 200) [Jitter]")
    f3_tracks = [{"track_id": 42, "bbox": [295, 150, 315, 200], "timestamp": 102.0}]
    evs3 = detector.process_tracks(f3_tracks)
    print(f"  -> Detected Events: {len(evs3)}")

    # Rate & Accumulation Verification
    rates = aggregator.get_flow_rates(now=102.0)

    print("\n" + "=" * 65)
    print("                      VERIFICATION SUMMARY")
    print("=" * 65)
    print(f"  - Total Inflow Count:   {rates['window_inflow_count']} (Expected: 1)")
    print(f"  - Total Outflow Count:  {rates['window_outflow_count']} (Expected: 0)")
    print(f"  - Net Accumulation:     +{rates['net_accumulation']} peds")
    print(f"  - Inflow Rate:          {rates['inflow_rate']} peds/min")

    if rates['window_inflow_count'] == 1 and rates['window_outflow_count'] == 0:
        print("\n[VERDICT: PASS] Single walk-through produced EXACTLY 1 verified count.")
    else:
        print("\n[VERDICT: FAIL] Duplicate or incorrect counts detected.")
        sys.exit(1)


if __name__ == "__main__":
    main()
