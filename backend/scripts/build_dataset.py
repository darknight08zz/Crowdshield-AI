"""
CROWDSHIELD DATASET BUILDER CLI
===============================
Reproducible command-line utility to generate ML-ready datasets from telemetry logs.

Usage:
    python scripts/build_dataset.py --input <telemetry_csv> --output <output_dir> --window 300 --horizon 300 --source MIXED_EXPLICIT

Note: DO NOT TRAIN ANY MODEL IN THIS SCRIPT.
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.dataset.builder import DatasetBuilder
from app.ai.training.data_loader import load_historical_telemetry


def generate_synthetic_telemetry(num_samples: int = 1200) -> pd.DataFrame:
    """
    Generates synthetic temporal sequence telemetry for dataset pipeline testing.
    Labeled explicitly as SYNTHETIC TEST DATA.
    """
    np.random.seed(42)
    rows = []

    # Generate 4 zones with 300 timestamps each (10-second sampling intervals)
    zones = ["ZONE-NORTH", "ZONE-SOUTH", "ZONE-EAST", "ZONE-WEST"]

    for zone in zones:
        base_ts = 1786600000
        curr_density = 0.20
        curr_speed = 1.30

        for i in range(300):
            ts_str = pd.to_datetime(base_ts + (i * 10), unit="s").isoformat() + "Z"

            # Create realistic gradual crowd density buildup in North and West zones
            if zone in ["ZONE-NORTH", "ZONE-WEST"] and i > 100:
                curr_density = min(0.92, curr_density + np.random.uniform(0.002, 0.008))
                curr_speed = max(0.20, 1.45 - (curr_density * 1.30))
            else:
                curr_density = max(0.05, min(0.45, curr_density + np.random.normal(0, 0.01)))
                curr_speed = max(0.80, min(1.50, 1.45 - (curr_density * 1.10)))

            inflow = round(curr_density * 160.0 + np.random.uniform(-5, 5), 1)
            outflow = round(max(10.0, (1.0 - curr_density) * 110.0 + np.random.uniform(-5, 5)), 1)
            conflict = round(min(0.95, max(0.05, curr_density * 0.75)), 3)
            reverse = round(min(0.95, max(0.01, curr_density * 0.60)), 3)
            blockage = round(min(0.95, max(0.05, curr_density * 0.70)), 3)

            rows.append({
                "timestamp": ts_str,
                "camera_id": f"CAM-{zone[-2:]}",
                "zone_id": zone,
                "event_id": "EVENT-PILOT-2026",
                "density": round(curr_density, 3),
                "inflow_rate": inflow,
                "outflow_rate": outflow,
                "average_speed": round(curr_speed, 2),
                "median_speed": round(max(0.15, curr_speed - 0.05), 2),
                "stationary_ratio": round(min(0.80, max(0.02, curr_density * 0.50)), 2),
                "reverse_flow_ratio": reverse,
                "direction_conflict_score": conflict,
                "blockage_score": blockage,
                "person_count": int(curr_density * 80),
                "tracked_person_count": int(curr_density * 75),
                "calibration_status": "HOMOGRAPHY",
                "telemetry_source": "live_cctv_gps",
                "processing_mode": "DEMO" if "DEMO" in zone else "LIVE",
                "confidence_score": 0.90,
                "is_degraded": False,
                "is_synthetic": True,
                "is_simulated": False,
            })

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="CrowdShield Dataset Builder CLI")
    parser.add_argument("--input", type=str, default=None, help="Input CSV path or directory containing telemetry")
    parser.add_argument("--output", type=str, default="data/dataset_v1", help="Output directory for generated dataset splits")
    parser.add_argument("--window", type=int, default=300, help="Feature window size in seconds (default 300s)")
    parser.add_argument("--horizon", type=int, default=300, help="Prediction horizon in seconds (default 300s)")
    parser.add_argument("--source", type=str, default="MIXED_EXPLICIT", choices=["REAL_ONLY", "DEMO_VIDEO", "SYNTHETIC", "MIXED_EXPLICIT"], help="Dataset provenance source filter")
    parser.add_argument("--split", type=str, default="CHRONOLOGICAL", choices=["CHRONOLOGICAL", "EVENT_LEVEL"], help="Dataset split strategy")
    parser.add_argument("--synthetic-test-data", action="store_true", help="Generate synthetic temporal sequence test telemetry if no input CSV provided")

    args = parser.parse_args()

    print("\n=======================================================")
    print("      CROWDSHIELD DATASET GENERATION PIPELINE          ")
    print("=======================================================")
    print(f"Feature Window Size   : {args.window} seconds")
    print(f"Prediction Horizon    : {args.horizon} seconds")
    print(f"Provenance Filter Mode: {args.source}")
    print(f"Split Strategy        : {args.split}")
    print("=======================================================\n")

    if args.input and os.path.exists(args.input):
        print(f"[BUILDER] Reading telemetry dataset from: {args.input}")
        telemetry_df = pd.read_csv(args.input)
    else:
        print("[BUILDER] No valid input CSV specified. Generating synthetic temporal sequence telemetry for pipeline verification...")
        telemetry_df = generate_synthetic_telemetry(num_samples=1200)

    print(f"[BUILDER] Loaded raw telemetry: {len(telemetry_df)} rows.")

    builder = DatasetBuilder(
        feature_window_seconds=args.window,
        prediction_horizon_seconds=args.horizon,
        source_mode=args.source,
        split_strategy=args.split
    )

    train_df, val_df, test_df, metadata = builder.build_dataset(telemetry_df)

    train_path, val_path, test_path, meta_path = builder.save_dataset_artifacts(
        output_dir=args.output,
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        metadata=metadata
    )

    print("\n[SUCCESS] Dataset generated successfully!")
    print(f" - Train Split : {train_path} ({len(train_df)} rows)")
    print(f" - Val Split   : {val_path} ({len(val_df)} rows)")
    print(f" - Test Split  : {test_path} ({len(test_df)} rows)")
    print(f" - Metadata    : {meta_path}")
    print(" - Model Fit   : NOT PERFORMED (Phase 3 Foundation Only)\n")


if __name__ == "__main__":
    main()
