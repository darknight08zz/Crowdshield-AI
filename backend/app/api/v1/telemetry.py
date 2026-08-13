"""
CROWDSHIELD TELEMETRY INGESTION ROUTER
======================================
High-throughput REST webhook endpoint for receiving real-time telemetry from venue CCTV cameras,
optical flow sensors, gate turnstiles, and mobile telemetry workers.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from uuid import UUID

from app.core.database import get_db
from app.ingestion.factory import get_ingestion_adapter
from app.models.zone import Zone

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
async def ingest_live_telemetry(payload: TelemetryIngestSchema, db: Session = Depends(get_db)):
    """
    High-throughput webhook endpoint for live camera, sensor, and turnstile telemetry.
    Pushes live metric pings into the hybrid ingestion buffer and updates PostgreSQL zone metrics.
    """
    adapter = get_ingestion_adapter()
    
    if hasattr(adapter, "update_camera_telemetry"):
        adapter.update_camera_telemetry(zone_id=payload.zone_id, camera_data=payload.dict())

    # Persist updated normalized density to database
    try:
        zone = db.query(Zone).filter(Zone.id == UUID(payload.zone_id)).first()
        if zone:
            # Normalize density (4.0 peds/m² = 1.0 critical max)
            normalized_density = min(1.0, max(0.0, payload.density_peds_m2 / 4.0))
            zone.current_density = normalized_density
            db.commit()
    except Exception as e:
        print(f"[!] Zone DB telemetry sync notice: {e}")

    return {
        "status": "success",
        "zone_id": payload.zone_id,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "ingestion_source": "live_webhook"
    }
