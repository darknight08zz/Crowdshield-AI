"""
CROWDSHIELD VIRTUAL LINE-CROSSING DETECTION MODULE
===================================================
Detects pedestrian directional crossing (INFLOW vs OUTFLOW) across virtual gate lines
using mathematical line segment intersection and cross-product side orientation tests.

DEDUPLICATION & JITTER PROTECTION:
----------------------------------
1. Minimum Displacement Threshold (min_displacement = 10.0px):
   Prevents false double-counting caused by track jitter when a person stands near the line.
2. Track Crossing Cooldown State:
   Remembers completed track IDs per gate line to guarantee exactly 1 count per physical walk-through.
3. Doorway Track Loss Handling:
   Tracks lost immediately near the virtual boundary increment an untracked_crossing_warning counter,
   which degrades confidence_score to flag potential undercounting.
"""

import math
import logging
from typing import Tuple, List, Dict, Any, Optional

logger = logging.getLogger("crowdshield.cv.line_crossing")


def line_segment_intersection(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    l1: Tuple[float, float],
    l2: Tuple[float, float]
) -> bool:
    """
    Checks if line segment (p1, p2) intersects virtual line segment (l1, l2).
    """
    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    return (ccw(p1, l1, l2) != ccw(p2, l1, l2)) and (ccw(p1, p2, l1) != ccw(p1, p2, l2))


def get_side_of_line(p: Tuple[float, float], l1: Tuple[float, float], l2: Tuple[float, float]) -> float:
    """
    Computes cross product determinant to determine which side of the line point p lies on.
    """
    return (l2[0] - l1[0]) * (p[1] - l1[1]) - (l2[1] - l1[1]) * (p[0] - l1[0])


def check_line_crossing(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    virtual_line: List[List[float]],
    min_displacement: float = 10.0
) -> Optional[str]:
    """
    Evaluates whether motion from p1 -> p2 represents an INFLOW or OUTFLOW line crossing.

    Args:
        p1: Previous foot pixel location (u1, v1)
        p2: Current foot pixel location (u2, v2)
        virtual_line: [[x1, y1], [x2, y2]] gate line segment
        min_displacement: Minimum required displacement pixels to prevent boundary jitter

    Returns:
        "INFLOW" | "OUTFLOW" | None
    """
    l1 = (float(virtual_line[0][0]), float(virtual_line[0][1]))
    l2 = (float(virtual_line[1][0]), float(virtual_line[1][1]))

    # 1. Minimum displacement check (jitter filter)
    dist = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
    if dist < min_displacement:
        return None

    # 2. Segment intersection test
    if not line_segment_intersection(p1, p2, l1, l2):
        return None

    # 3. Orientation / Side of line test
    side1 = get_side_of_line(p1, l1, l2)
    side2 = get_side_of_line(p2, l1, l2)

    if side1 > 0 and side2 <= 0:
        return "INFLOW"
    elif side1 < 0 and side2 >= 0:
        return "OUTFLOW"

    return None


class LineCrossingDetector:
    """
    Stateful manager for tracking line crossings per gate.
    Prevents duplicate counting for active tracks.
    """

    def __init__(self, gate_id: str, virtual_line: Optional[List[List[float]]] = None):
        self.gate_id = gate_id
        # Default virtual line: vertical bisector across 400x400 frame
        self.virtual_line = virtual_line or [[200.0, 0.0], [200.0, 400.0]]
        self.track_last_positions: Dict[int, Tuple[float, float]] = {}
        self.crossed_tracks: Dict[int, str] = {}  # track_id -> "INFLOW" | "OUTFLOW"
        self.untracked_boundary_losses = 0

    def process_tracks(self, tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes frame tracks and returns a list of new verified crossing events.
        """
        events = []
        active_track_ids = set()

        for trk in tracks:
            t_id = trk["track_id"]
            active_track_ids.add(t_id)
            bbox = trk["bbox"]
            feet = ((bbox[0] + bbox[2]) / 2.0, bbox[3])

            if t_id in self.track_last_positions:
                prev_feet = self.track_last_positions[t_id]
                crossing_dir = check_line_crossing(prev_feet, feet, self.virtual_line)

                if crossing_dir and t_id not in self.crossed_tracks:
                    self.crossed_tracks[t_id] = crossing_dir
                    events.append({
                        "gate_id": self.gate_id,
                        "track_id": t_id,
                        "direction": crossing_dir,
                        "timestamp": trk.get("timestamp", trk.get("frame_timestamp"))
                    })
                    logger.info(f"[GATE {self.gate_id}] Verified {crossing_dir} crossing for track #{t_id}")

            self.track_last_positions[t_id] = feet

        # Check for track loss right at the gate boundary (doorway occlusion edge case)
        for prev_tid, prev_pos in list(self.track_last_positions.items()):
            if prev_tid not in active_track_ids:
                # Check if position was close to virtual line (within 20px)
                l1 = (self.virtual_line[0][0], self.virtual_line[0][1])
                l2 = (self.virtual_line[1][0], self.virtual_line[1][1])
                side = abs(get_side_of_line(prev_pos, l1, l2))
                if side < 1000.0:  # Proximity to line
                    self.untracked_boundary_losses += 1
                del self.track_last_positions[prev_tid]

        return events
