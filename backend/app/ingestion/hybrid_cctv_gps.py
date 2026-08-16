"""
CROWDSHIELD HYBRID CCTV + CITIZEN GPS INGESTION ADAPTER
=======================================================
Processes optical density maps, trajectory flow vectors, and person detection telemetry
from camera streams, cross-referenced with active Citizen app GPS location telemetry.

Ingestion Contract:
-------------------
Produces canonical feature vector keys expected by ai/features.py, plus confidence_score and provenance:
- Optical density estimation (peds/m² converted to occupancy ratio)
- Directional velocity vectors (inflow, outflow, avg speed)
- Counter-flow angle variance (direction_conflict_score & reverse_flow_ratio)
- Spatial sub-area grid velocity variance (blockage_score)
- Citizen GPS active user cross-check multiplier
- Full provenance metadata (processing_mode, calibration_status, telemetry_source, is_degraded, is_synthetic)
"""

from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.ingestion.base import BaseSensorIngestion
from app.ingestion.synthetic import SyntheticSensorIngestion
from app.ingestion.quality import evaluate_telemetry_quality
from app.ingestion.cv.pipeline import CVPipelineManager
from app.models.zone import Zone
from app.models.gate import Gate
from app.models.incident import Incident
from app.models.user import User, UserRoleEnum


class HybridCCTVGPSIngestion(BaseSensorIngestion):
    """
    Live Hybrid Sensing Ingestion Adapter:
    Processes real camera optical flow & density metrics with GPS cross-verification and CVPipelineManager.
    """

    def __init__(self, fallback_adapter: Optional[BaseSensorIngestion] = None, processing_mode: str = "LIVE"):
        self.fallback = fallback_adapter or SyntheticSensorIngestion()
        self.processing_mode = processing_mode
        self.camera_buffers: Dict[str, Dict[str, Any]] = {}
        self.cv_pipelines: Dict[str, CVPipelineManager] = {}

    def update_camera_telemetry(self, zone_id: str, camera_data: Dict[str, Any]):
        """
        Ingestion webhook/queue entrypoint for live computer vision inference workers.
        Accepts optical density, optical flow vectors, and directional conflict data.
        """
        self.camera_buffers[str(zone_id)] = {
            "timestamp": datetime.now(timezone.utc),
            "camera_id": camera_data.get("camera_id", "CAM-01"),
            "raw_density_peds_m2": camera_data.get("density_peds_m2", 1.8),
            "inflow_peds_min": camera_data.get("inflow_peds_min", 95.0),
            "outflow_peds_min": camera_data.get("outflow_peds_min", 85.0),
            "avg_speed_ms": camera_data.get("avg_speed_ms", 1.1),
            "reverse_flow_ratio": camera_data.get("reverse_flow_ratio", 0.12),
            "blockage_score": camera_data.get("blockage_score", 0.15),
            "direction_conflict_score": camera_data.get("direction_conflict_score", 0.20),
            "active_cameras": camera_data.get("active_cameras", 4),
            "total_cameras": camera_data.get("total_cameras", 4)
        }

    def get_zone_features(self, zone_id: Any, db: Session) -> Dict[str, Any]:
        zone_str = str(zone_id)

        try:
            # 1. Fetch Zone and Database context
            zone = db.query(Zone).filter(Zone.id == UUID(zone_str)).first() if db else None
            zone_area_m2 = float(getattr(zone, "area_m2", 500.0)) if zone else 500.0
            is_calibrated = (getattr(zone, "is_calibrated", 1.0) == 1.0) if zone else False
            homography = getattr(zone, "homography_matrix", None) if zone else None

            # 2. Extract Active GPS Pings from DB
            active_gps_users = db.query(User).filter(
                User.role == UserRoleEnum.CITIZEN,
                User.is_active == True
            ).count() if db else 0

            # 3. Retrieve Live CCTV Optical Telemetry Buffer
            cam_data = self.camera_buffers.get(zone_str)
            now = datetime.now(timezone.utc)

            if not cam_data:
                # If no live feed received yet, trigger graceful fallback with degraded score
                fallback_data = self.fallback.get_zone_features(zone_id, db)
                quality = evaluate_telemetry_quality(
                    feed_age_seconds=999.0,
                    active_cameras_ratio=0.0,
                    gps_sample_count=active_gps_users
                )
                fallback_data["confidence_score"] = quality["confidence_score"]
                fallback_data["telemetry_source"] = "live_cctv_gps"
                fallback_data["processing_mode"] = self.processing_mode
                fallback_data["calibration_status"] = "HOMOGRAPHY" if is_calibrated else "UNCALIBRATED"
                fallback_data["is_degraded"] = True
                fallback_data["is_synthetic"] = (self.processing_mode == "SIMULATION")
                fallback_data["quality_breakdown"] = quality["quality_breakdown"]
                return fallback_data

            # 4. Telemetry Freshness & Data Quality Evaluation
            feed_age = (now - cam_data["timestamp"]).total_seconds()
            active_ratio = cam_data["active_cameras"] / max(1, cam_data["total_cameras"])

            quality = evaluate_telemetry_quality(
                feed_age_seconds=feed_age,
                active_cameras_ratio=active_ratio,
                gps_sample_count=active_gps_users
            )

            # If telemetry is too stale (>30s), fall back to degraded telemetry
            if feed_age > 30.0:
                fallback_data = self.fallback.get_zone_features(zone_id, db)
                fallback_data["confidence_score"] = quality["confidence_score"]
                fallback_data["telemetry_source"] = "live_cctv_gps"
                fallback_data["processing_mode"] = self.processing_mode
                fallback_data["calibration_status"] = "HOMOGRAPHY" if is_calibrated else "UNCALIBRATED"
                fallback_data["is_degraded"] = True
                fallback_data["is_synthetic"] = (self.processing_mode == "SIMULATION")
                fallback_data["quality_breakdown"] = quality["quality_breakdown"]
                return fallback_data

            # 5. Run CV Pipeline Manager
            if zone_str not in self.cv_pipelines:
                self.cv_pipelines[zone_str] = CVPipelineManager(
                    zone_id=zone_str,
                    camera_id=cam_data.get("camera_id", "CAM-01"),
                    zone_area_m2=zone_area_m2,
                    homography_matrix=homography,
                    is_calibrated=is_calibrated,
                    processing_mode=self.processing_mode
                )

            cv_output = self.cv_pipelines[zone_str].process_frame(cam_data)

            # Compute Hybrid Density (CCTV Optical Density + GPS Cross-Check)
            cctv_density_peds_m2 = cv_output["density"]
            gps_estimated_density = active_gps_users / max(1.0, zone_area_m2 * 0.15)
            effective_density_peds_m2 = max(cctv_density_peds_m2, gps_estimated_density)
            current_density = min(1.0, effective_density_peds_m2 / 4.0)

            # 6. Database Incident & Gate Metrics
            ten_mins_ago = datetime.utcnow() - timedelta(minutes=10)
            incident_count = db.query(Incident).filter(
                Incident.zone_id == UUID(zone_str),
                Incident.created_at >= ten_mins_ago
            ).count() if db else 0

            gates = db.query(Gate).filter(Gate.zone_id == UUID(zone_str)).all() if db else []
            total_capacity = sum([g.capacity_per_min for g in gates]) if gates else 300
            restricted_gates = len([g for g in gates if g.status in ["restricted", "closed"]])
            gate_utilization = min(1.0, (cam_data["inflow_peds_min"] / max(1, total_capacity)) + (0.15 * restricted_gates))

            base_confidence = min(quality["confidence_score"], cv_output["confidence_score"])
            if not is_calibrated:
                base_confidence = min(base_confidence, 0.75)
                calib_warning = "UNCALIBRATED ZONE: Using estimated default floor area (500m²). Accuracy degraded."
            else:
                calib_warning = None

            final_confidence = round(base_confidence, 3)

            return {
                "current_density": round(current_density, 3),
                "inflow_rate": round(float(cam_data["inflow_peds_min"]), 1),
                "outflow_rate": round(float(cam_data["outflow_peds_min"]), 1),
                "avg_pedestrian_speed": round(float(cam_data["avg_speed_ms"]), 2),
                "direction_conflict_score": round(float(cam_data["direction_conflict_score"]), 3),
                "gate_capacity_utilization": round(gate_utilization, 3),
                "recent_incident_count_10min": float(incident_count),
                "reverse_flow_ratio": round(float(cam_data["reverse_flow_ratio"]), 3),
                "blockage_score": round(float(cam_data["blockage_score"]), 3),
                "confidence_score": final_confidence,
                "telemetry_source": "live_cctv_gps",
                "processing_mode": self.processing_mode,
                "calibration_status": "HOMOGRAPHY" if is_calibrated else "UNCALIBRATED",
                "is_degraded": quality["is_degraded"] or (not is_calibrated),
                "is_synthetic": (self.processing_mode == "SIMULATION"),
                "quality_breakdown": {
                    **quality["quality_breakdown"],
                    "cv_strategy": cv_output.get("behavior_classification", "NORMAL"),
                    "is_calibrated": is_calibrated,
                    "calibration_warning": calib_warning
                }
            }

        except Exception as e:
            # High-reliability fallback if processing error occurs
            print(f"[!] Ingestion error on zone {zone_id}: {e}. Triggering degraded telemetry output.")
            fallback_data = self.fallback.get_zone_features(zone_id, db)
            fallback_data["confidence_score"] = 0.30
            fallback_data["telemetry_source"] = "live_cctv_gps"
            fallback_data["processing_mode"] = self.processing_mode
            fallback_data["is_degraded"] = True
            fallback_data["is_synthetic"] = (self.processing_mode == "SIMULATION")
            return fallback_data
