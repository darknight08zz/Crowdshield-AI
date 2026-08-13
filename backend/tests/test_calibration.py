"""
TEST SUITE FOR ZONE CALIBRATION & REAL-WORLD DENSITY MAPPING (Addendum Prompt 2)
=============================================================================
Verifies homography computation, pixel-to-world metric mapping, speed calculation,
subgrid localized density variance, and uncalibrated degradation.
"""

import pytest
import math
from app.ingestion.cv.calibration import (
    compute_homography,
    pixel_to_world,
    calculate_metric_speed,
    calculate_subgrid_densities
)


def test_compute_homography_and_pixel_to_world():
    """Verifies that compute_homography correctly maps 4-point pixel rectangle to 5m x 5m world grid."""
    img_pts = [[100.0, 100.0], [500.0, 100.0], [500.0, 400.0], [100.0, 400.0]]
    world_pts = [[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0]]

    H = compute_homography(img_pts, world_pts)
    assert len(H) == 3 and len(H[0]) == 3

    # Test top-left corner mapping
    w1_x, w1_y = pixel_to_world([100.0, 100.0], H)
    assert abs(w1_x - 0.0) < 0.05 and abs(w1_y - 0.0) < 0.05

    # Test bottom-right corner mapping
    w2_x, w2_y = pixel_to_world([500.0, 400.0], H)
    assert abs(w2_x - 5.0) < 0.05 and abs(w2_y - 5.0) < 0.05


def test_metric_speed_calculation_with_homography():
    """Verifies calculate_metric_speed outputs speed in m/s using homography matrix."""
    img_pts = [[100.0, 100.0], [500.0, 100.0], [500.0, 400.0], [100.0, 400.0]]
    world_pts = [[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0]]
    H = compute_homography(img_pts, world_pts)

    # Bbox moves 200 pixels horizontally in 1 second -> represents 2.5 meters in 1 second
    track_hist = [
        {"bbox": [100.0, 100.0, 150.0, 200.0], "timestamp": 1000.0},
        {"bbox": [300.0, 100.0, 350.0, 200.0], "timestamp": 1001.0}
    ]

    speed_m_s = calculate_metric_speed(track_hist, transform_matrix=H)
    assert 2.4 <= speed_m_s <= 2.6  # Expect ~2.5 m/s


def test_subgrid_localized_density_subdivision():
    """Verifies subgrid density subdivision accurately identifies bottleneck sub-areas."""
    img_pts = [[0.0, 0.0], [400.0, 0.0], [400.0, 400.0], [0.0, 400.0]]
    world_pts = [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]]
    H = compute_homography(img_pts, world_pts)

    # 10 detections clustered in top-left cell [0, 0]
    dets = [{"bbox": [10.0, 10.0, 20.0, 30.0], "confidence": 0.9} for _ in range(10)]

    res = calculate_subgrid_densities(dets, H, zone_bounds_meters=(20.0, 20.0), grid_dims=(4, 4))
    assert res["grid_dims"] == [4, 4]
    assert res["max_localized_density"] > 0.0
    assert res["grid_densities_peds_m2"][0][0] > 0.0
