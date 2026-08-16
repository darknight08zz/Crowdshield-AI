"""
BUILD DATASET V2 CLI SCRIPT (PHASE 5)
=====================================
Builds Dataset V2 from existing telemetry / benchmark data,
saves CSVs and metadata.json to backend/data/dataset_v2.
"""

import sys
import os
import json
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.dataset.builder_v2 import DatasetBuilderV2


def generate_benchmark_telemetry(num_samples: int = 1200) -> pd.DataFrame:
    """Generates benchmark telemetry sequence for testing Dataset V2 builder."""
    np.random.seed(42)
    timestamps = pd.date_range(start="2026-08-14 10:00:00", periods=num_samples, freq="10s")

    t_val = np.linspace(0, 4 * np.pi, num_samples)
    density = np.clip(0.3 + 0.5 * np.sin(t_val) + np.random.normal(0, 0.05, num_samples), 0.05, 1.8)
    speed = np.clip(1.4 - 0.6 * density + np.random.normal(0, 0.05, num_samples), 0.1, 2.0)
    inflow = np.clip(50.0 + 80.0 * density + np.random.normal(0, 5, num_samples), 10.0, 300.0)
    outflow = np.clip(60.0 - 20.0 * density + np.random.normal(0, 5, num_samples), 5.0, 200.0)
    conflict = np.clip(0.1 + 0.4 * density, 0.0, 1.0)
    stationary = np.clip(0.05 + 0.3 * density, 0.0, 1.0)
    blockage = np.clip(0.05 + 0.35 * density, 0.0, 1.0)
    person_cnt = (density * 80).astype(int)
    tracked_cnt = (person_cnt * 0.95).astype(int)

    df = pd.DataFrame({
        "timestamp": [ts.isoformat() + "Z" for ts in timestamps],
        "camera_id": ["cam_01"] * (num_samples // 2) + ["cam_02"] * (num_samples - num_samples // 2),
        "zone_id": ["zone_A"] * (num_samples // 4) + ["zone_B"] * (num_samples // 4) + ["zone_C"] * (num_samples // 4) + ["zone_D"] * (num_samples - 3 * (num_samples // 4)),
        "event_id": ["event_benchmark_01"] * num_samples,
        "density": density,
        "average_speed": speed,
        "median_speed": speed * 0.95,
        "inflow_rate": inflow,
        "outflow_rate": outflow,
        "stationary_ratio": stationary,
        "reverse_flow_ratio": stationary * 0.8,
        "direction_conflict_score": conflict,
        "blockage_score": blockage,
        "person_count": person_cnt,
        "tracked_person_count": tracked_cnt,
        "telemetry_source": ["MIXED_EXPLICIT"] * num_samples,
    })
    return df


def main():
    print("==================================================")
    print(" BUILDING CROWDSHIELD DATASET V2 (PHASE 5)")
    print("==================================================")

    v1_telemetry_path = os.path.join("data", "dataset", "dataset_full.csv")
    if os.path.exists(v1_telemetry_path):
        print(f"Loading raw telemetry from: {v1_telemetry_path}")
        raw_df = pd.read_csv(v1_telemetry_path)
    else:
        print("Generating benchmark telemetry...")
        raw_df = generate_benchmark_telemetry(num_samples=1200)

    v2_builder = DatasetBuilderV2(data_dir="data/dataset_v2")
    results = v2_builder.build_dataset_v2(raw_df=raw_df, horizon_steps=30)

    meta = results["metadata"]
    print("\n--- DATASET V2 METADATA SUMMARY ---")
    print(f"Dataset Version:     {meta['dataset_version']}")
    print(f"Total Samples:       {meta['total_samples']}")
    print(f"Train / Val / Test:  {meta['train_samples']} / {meta['val_samples']} / {meta['test_samples']}")
    print(f"Independent Events:  {meta['unique_events']}")
    print(f"Cameras / Zones:     {meta['unique_cameras']} / {meta['unique_zones']}")
    print(f"Split Strategy:      {meta['split_strategy']}")
    print(f"Generalization:      {meta['generalization_status']}")
    print(f"Primary Target:      {meta['primary_target']}")
    print(f"Positive Ratio:      {meta['target_distribution']['EARLY_ESCALATION_5M']['positive_ratio']:.4f}")
    print(f"Risk Delta 5M Mean:  {meta['target_distribution']['RISK_DELTA_5M']['mean']:.2f}")

    print(f"\nDataset V2 files successfully written to backend/data/dataset_v2/")


if __name__ == "__main__":
    main()
