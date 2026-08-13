"""
CROWDSHIELD ZONE CALIBRATION VALIDATION TOOL
=============================================
Sanity check script for Event Administrators to verify homography or area calibration
before live event deployment.

USAGE:
python scripts/validate_calibration.py --zone_id <UUID> --p1 100,200 --p2 400,200 --known_distance 5.0
"""

import sys
import os
import math
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.cv.calibration import compute_homography, pixel_to_world


def validate_calibration_points(
    image_p1: list,
    image_p2: list,
    known_distance_meters: float,
    homography_matrix: list
) -> dict:
    """
    Transforms two test pixel points to physical ground plane coordinates
    and checks accuracy against known real-world distance.
    """
    w1_x, w1_y = pixel_to_world(image_p1, homography_matrix)
    w2_x, w2_y = pixel_to_world(image_p2, homography_matrix)

    estimated_distance = math.sqrt((w2_x - w1_x) ** 2 + (w2_y - w1_y) ** 2)
    error_meters = abs(estimated_distance - known_distance_meters)
    error_percentage = (error_meters / max(0.001, known_distance_meters)) * 100.0

    is_valid = error_percentage <= 5.0  # Pass threshold: <= 5% distance error

    return {
        "status": "PASS" if is_valid else "WARN",
        "known_distance_m": known_distance_meters,
        "estimated_distance_m": round(estimated_distance, 3),
        "error_meters": round(error_meters, 3),
        "error_percentage": round(error_percentage, 2),
        "verdict": "Calibration verified accurate (<=5% error)" if is_valid else "High error (>5%). Re-calibrate reference points."
    }


def main():
    parser = argparse.ArgumentParser(description="Validate CrowdShield Zone Camera Calibration")
    parser.add_argument("--known_distance", type=float, default=5.0, help="Known ground distance in meters between reference markers")
    args = parser.parse_args()

    # Sample 4-point reference correspondences (5m x 5m floor tile grid)
    img_pts = [[100, 100], [500, 100], [500, 400], [100, 400]]
    world_pts = [[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0]]

    print("\n[CALIBRATION VALIDATOR] Computing Homography Matrix...")
    H = compute_homography(img_pts, world_pts)

    print("Testing Verification Segment: Image [100,100] -> [500,100] (Expected: 5.0 meters)")
    res = validate_calibration_points([100, 100], [500, 100], args.known_distance, H)

    print(f"\n================ CALIBRATION VERDICT: {res['status']} ================")
    print(f"  - Known Physical Distance:    {res['known_distance_m']} m")
    print(f"  - System Estimated Distance: {res['estimated_distance_m']} m")
    print(f"  - Absolute Metric Error:     {res['error_meters']} m")
    print(f"  - Percentage Error:          {res['error_percentage']}%")
    print(f"  - Verdict:                   {res['verdict']}\n")


if __name__ == "__main__":
    main()
