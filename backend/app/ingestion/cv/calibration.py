"""
CROWDSHIELD CAMERA & ZONE HOMOGRAPHY CALIBRATION MODULE
======================================================
Provides mathematical mapping from camera image pixel space (u, v)
to physical metric ground plane space (x_meters, y_meters).

Solves the pixel-vs-meters problem:
-----------------------------------
1. Raw pixel displacement varies by camera lens tilt, height, and distance from camera.
2. Homography transforms 4+ image reference points (e.g. tile corners) to known world coordinates.
3. Enables accurate real-world speed calculation (m/s) and sub-zone localized density mapping (peds/m2).
"""

import math
import logging
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

logger = logging.getLogger("crowdshield.cv.calibration")


def compute_homography(
    image_points: List[List[float]],
    world_points: List[List[float]]
) -> List[List[float]]:
    """
    Computes a 3x3 Homography transformation matrix from >= 4 point correspondences.

    Args:
        image_points: List of [u, v] pixel coordinates
        world_points: List of [X_meters, Y_meters] physical ground plane coordinates

    Returns:
        3x3 matrix as List[List[float]]
    """
    if len(image_points) < 4 or len(world_points) < 4:
        raise ValueError("Homography computation requires at least 4 reference point pairs.")

    try:
        import cv2
        pts_src = np.array(image_points, dtype=np.float32)
        pts_dst = np.array(world_points, dtype=np.float32)
        h_matrix, _ = cv2.findHomography(pts_src, pts_dst, cv2.RANSAC, 5.0)
        if h_matrix is not None:
            return h_matrix.tolist()
    except Exception as e:
        logger.warning(f"[CV CALIBRATION] OpenCV findHomography fallback to SVD: {e}")

    # NumPy DLT (Direct Linear Transform) Fallback Implementation
    num_pts = min(len(image_points), len(world_points))
    A = []
    for i in range(num_pts):
        u, v = image_points[i][0], image_points[i][1]
        x, y = world_points[i][0], world_points[i][1]
        A.append([-u, -v, -1, 0, 0, 0, u * x, v * x, x])
        A.append([0, 0, 0, -u, -v, -1, u * y, v * y, y])

    A = np.array(A, dtype=np.float64)
    _, _, Vh = np.linalg.svd(A)
    H = Vh[-1].reshape(3, 3)
    H = H / H[2, 2]
    return H.tolist()


def pixel_to_world(
    point: Tuple[float, float],
    transform_matrix: List[List[float]]
) -> Tuple[float, float]:
    """
    Transforms a single camera pixel coordinate (u, v) to ground plane world meters (X, Y).
    """
    u, v = point[0], point[1]
    H = np.array(transform_matrix, dtype=np.float64)
    pt_vec = np.array([u, v, 1.0], dtype=np.float64)

    world_pt = np.dot(H, pt_vec)
    scale = world_pt[2] if abs(world_pt[2]) > 1e-7 else 1e-7
    x_meters = world_pt[0] / scale
    y_meters = world_pt[1] / scale

    return float(x_meters), float(y_meters)


def calculate_metric_speed(
    track_history: List[Dict[str, Any]],
    transform_matrix: Optional[List[List[float]]] = None,
    pixel_scale: float = 0.05
) -> float:
    """
    Computes pedestrian velocity in physical m/s from bounding box track history.

    If homography matrix is present, converts pixels to ground meters via pixel_to_world().
    Otherwise, applies linear pixel scale fallback.
    """
    if len(track_history) < 2:
        return 1.10  # Default nominal walking speed (m/s)

    p1 = track_history[-2]
    p2 = track_history[-1]

    dt = max(0.001, p2["timestamp"] - p1["timestamp"])

    # Center bottom of bounding box represents feet location on ground plane
    b1 = p1["bbox"]
    b2 = p2["bbox"]
    feet1 = ((b1[0] + b1[2]) / 2.0, b1[3])
    feet2 = ((b2[0] + b2[2]) / 2.0, b2[3])

    if transform_matrix is not None:
        w1_x, w1_y = pixel_to_world(feet1, transform_matrix)
        w2_x, w2_y = pixel_to_world(feet2, transform_matrix)
        distance_meters = math.sqrt((w2_x - w1_x) ** 2 + (w2_y - w1_y) ** 2)
    else:
        # Uncalibrated fallback: linear pixel scaling
        dx = (feet2[0] - feet1[0]) * pixel_scale
        dy = (feet2[1] - feet1[1]) * pixel_scale
        distance_meters = math.sqrt(dx ** 2 + dy ** 2)

    speed_m_s = distance_meters / dt
    return round(min(5.0, speed_m_s), 2)  # Cap speed to realistic 5 m/s


def calculate_subgrid_densities(
    detections: List[Dict[str, Any]],
    transform_matrix: Optional[List[List[float]]],
    zone_bounds_meters: Tuple[float, float] = (20.0, 25.0),
    grid_dims: Tuple[int, int] = (4, 4)
) -> Dict[str, Any]:
    """
    Subdivides zone into a grid (e.g. 4x4) and calculates localized density variations.
    Enables identification of localized bottleneck hotspots within a large zone.
    """
    rows, cols = grid_dims
    grid_counts = np.zeros((rows, cols), dtype=np.int32)
    width_m, height_m = zone_bounds_meters
    cell_w = width_m / float(cols)
    cell_h = height_m / float(rows)
    cell_area = cell_w * cell_h

    for det in detections:
        bbox = det["bbox"]
        feet = ((bbox[0] + bbox[2]) / 2.0, bbox[3])

        if transform_matrix is not None:
            wx, wy = pixel_to_world(feet, transform_matrix)
        else:
            # Normalized approximation
            wx, wy = feet[0] * 0.025, feet[1] * 0.025

        col_idx = min(cols - 1, max(0, int(wx / cell_w)))
        row_idx = min(rows - 1, max(0, int(wy / cell_h)))
        grid_counts[row_idx, col_idx] += 1

    grid_densities = (grid_counts / cell_area).round(2).tolist()
    max_cell_density = float(np.max(grid_densities))

    return {
        "grid_dims": [rows, cols],
        "grid_densities_peds_m2": grid_densities,
        "max_localized_density": max_cell_density,
        "variance": round(float(np.var(grid_densities)), 3)
    }
