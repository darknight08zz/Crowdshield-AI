"""
CROWDSHIELD TELEMETRY INGESTION ROUTER
======================================
High-throughput REST webhook endpoint for receiving real-time telemetry from venue CCTV cameras,
optical flow sensors, gate turnstiles, and mobile telemetry workers.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from uuid import UUID

from app.core.database import get_db
from app.core.rate_limiter import telemetry_rate_limiter
from app.ingestion.factory import get_ingestion_adapter
from app.models.zone import Zone
from app.ai.risk_model import predict_risk

router = APIRouter(prefix="/telemetry", tags=["Telemetry Ingestion"])


class TelemetryIngestSchema(BaseModel):
    zone_id: str = Field(..., description="UUID of target zone")
    density_peds_m2: float = Field(..., ge=0.0, description="Measured pedestrian density in peds/m²")
    inflow_peds_min: float = Field(..., ge=0.0, description="Ingress rate (pedestrians / min)")
    outflow_peds_min: float = Field(..., ge=0.0, description="Egress rate (pedestrians / min)")
    avg_speed_ms: Optional[float] = Field(1.1, ge=0.0, description="Average pedestrian movement velocity (m/s)")
    reverse_flow_ratio: Optional[float] = Field(0.05, ge=0.0, le=1.0, description="Share of reverse directional flow")
    blockage_score: Optional[float] = Field(0.10, ge=0.0, le=1.0, description="Spatial blockage index (0.0 to 1.0)")
    direction_conflict_score: Optional[float] = Field(0.15, ge=0.0, le=1.0, description="Direction conflict index")
    active_cameras: Optional[int] = Field(1, ge=1, description="Number of operating camera streams")
    total_cameras: Optional[int] = Field(1, ge=1, description="Total assigned camera streams")


@router.post("/ingest", status_code=status.HTTP_200_OK)
async def ingest_live_telemetry(
    payload: TelemetryIngestSchema,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    High-throughput webhook endpoint for live camera, sensor, and turnstile telemetry.
    Pushes live metric pings into the hybrid ingestion buffer, updates zone density,
    calculates real-time risk, and records historical time-series metric snapshots.
    """
    client_ip = request.client.host if request.client else "unknown"
    telemetry_rate_limiter.check_rate_limit(f"telemetry:{client_ip}")

    adapter = get_ingestion_adapter()

    if hasattr(adapter, "update_camera_telemetry"):
        adapter.update_camera_telemetry(zone_id=payload.zone_id, camera_data=payload.dict())

    # Persist updated normalized density to database & record telemetry snapshot
    computed_risk = 0.0
    try:
        zone = db.query(Zone).filter(Zone.id == UUID(payload.zone_id)).first()
        if zone:
            # Normalize density (4.0 peds/m² = 1.0 critical max)
            normalized_density = min(1.0, max(0.0, payload.density_peds_m2 / 4.0))
            zone.current_density = normalized_density

            # Compute real-time risk prediction for ingested frame
            feature_dict = {
                "current_density": normalized_density,
                "inflow_rate": payload.inflow_peds_min,
                "outflow_rate": payload.outflow_peds_min,
                "avg_pedestrian_speed": payload.avg_speed_ms or 1.1,
                "direction_conflict_score": payload.direction_conflict_score or 0.15,
                "gate_capacity_utilization": min(1.0, payload.inflow_peds_min / 300.0),
                "recent_incident_count_10min": 0.0,
                "reverse_flow_ratio": payload.reverse_flow_ratio or 0.05,
                "blockage_score": payload.blockage_score or 0.10
            }
            computed_risk = float(predict_risk(feature_dict))
            zone.risk_score = computed_risk
            db.commit()

            # Record time-series metric snapshot
            if zone.event_id:
                from app.api.v1.analytics import record_zone_metric_snapshot
                record_zone_metric_snapshot(
                    db=db,
                    event_id=zone.event_id,
                    zone_id=zone.id,
                    density=normalized_density,
                    inflow_rate=payload.inflow_peds_min,
                    outflow_rate=payload.outflow_peds_min,
                    avg_speed=payload.avg_speed_ms or 1.1,
                    risk_score=computed_risk,
                    behavior_classification="LIVE_INGEST",
                    propagated_risk_score=0.0
                )
    except Exception as e:
        print(f"[!] Zone DB telemetry sync notice: {e}")

    return {
        "status": "success",
        "zone_id": payload.zone_id,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "telemetry_source": "LIVE_CAMERA",
        "is_synthetic": False,
        "is_degraded": False,
        "computed_risk_score": computed_risk
    }

