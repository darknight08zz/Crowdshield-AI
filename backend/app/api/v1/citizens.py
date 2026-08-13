from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.security import require_role, UserPayload
from app.models import Incident, Zone, Event, Gate
from app.schemas.incident import IncidentCreate, IncidentResponse, IncidentStatusUpdate
from app.schemas.zone import ZoneResponse
from app.services.audit_service import log_action

router = APIRouter(prefix="/citizens", tags=["Citizens"])


from app.core.rate_limit import incident_rate_limiter


@router.post(
    "/incidents",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_role("citizen", "field_officer", "operator", "event_admin", "system_admin")),
        Depends(incident_rate_limiter)
    ]
)
async def report_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("citizen", "field_officer", "operator", "event_admin", "system_admin"))
):
    """
    Submits a crowd safety or medical emergency incident report.
    Allowed roles: citizen, field_officer, operator, event_admin, system_admin
    """
    zone = db.query(Zone).filter(Zone.id == payload.zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Specified Zone ID not found.")

    incident = Incident(
        reporter_id=UUID(current_user.id) if current_user.id else None,
        zone_id=payload.zone_id,
        type=payload.type,
        description=payload.description,
        media_url=payload.media_url
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if current_user.id else None,
        action="REPORT_INCIDENT",
        target=f"incident:{incident.id}",
        after_state={"type": payload.type, "zone_id": str(payload.zone_id)}
    )

    return incident


@router.get(
    "/incidents",
    response_model=List[IncidentResponse],
    dependencies=[Depends(require_role("citizen", "field_officer", "operator", "event_admin", "system_admin"))]
)
async def list_incidents(
    db: Session = Depends(get_db)
):
    """
    Retrieves list of incidents.
    """
    return db.query(Incident).order_by(Incident.created_at.desc()).all()


@router.patch(
    "/incidents/{incident_id}/status",
    response_model=IncidentResponse,
    dependencies=[Depends(require_role("field_officer", "operator", "event_admin", "system_admin"))]
)
async def update_incident_status(
    incident_id: UUID,
    payload: IncidentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("field_officer", "operator", "event_admin", "system_admin"))
):
    """
    Updates status of an incident.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")

    before_status = incident.status
    incident.status = payload.status
    db.commit()
    db.refresh(incident)

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if current_user.id else None,
        action="UPDATE_INCIDENT_STATUS",
        target=f"incident:{incident.id}",
        before_state={"status": str(before_status)},
        after_state={"status": str(payload.status)}
    )

    return incident



@router.get(
    "/zones",
    response_model=List[ZoneResponse],
    dependencies=[Depends(require_role("citizen", "field_officer", "operator", "event_admin", "system_admin"))]
)
async def get_live_zones(db: Session = Depends(get_db)):
    """
    Retrieves live zone density & risk status for safer routing and citizen risk map overlay.
    Allowed roles: ALL authenticated roles
    """
    zones = db.query(Zone).all()
    return zones


@router.get(
    "/zones/{zone_id}/density-grid",
    dependencies=[Depends(require_role("citizen", "field_officer", "operator", "event_admin", "system_admin"))]
)
async def get_citizen_zone_density_grid(
    zone_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves sub-zone density grid matrix for citizen map heatmap canvas overlay.
    """
    from app.api.v1.operator import get_zone_density_grid
    return await get_zone_density_grid(zone_id=zone_id, grid_rows=8, grid_cols=8, db=db)



@router.get("/map-data")
async def get_map_data(db: Session = Depends(get_db)):
    """
    Retrieves map overview telemetry combining event details, zone metrics, and gate choke-points.
    """
    active_event = db.query(Event).filter(Event.status == "active").first()
    if not active_event:
        active_event = db.query(Event).first()

    event_info = {
        "id": str(active_event.id) if active_event else None,
        "name": active_event.name if active_event else None,
        "venue": active_event.venue if active_event else None,
        "date": active_event.date.isoformat() if (active_event and active_event.date) else None,
        "status": active_event.status if active_event else None,
    }

    db_zones = db.query(Zone).all()
    zones_data = []
    if db_zones:
        for z in db_zones:
            zones_data.append({
                "id": str(z.id),
                "name": z.name,
                "capacity": z.capacity,
                "current_density": float(z.current_density) if z.current_density is not None else 0.0,
                "risk_score": float(z.risk_score) if z.risk_score is not None else 0.0,
                "status": "CRITICAL SURGE" if (z.risk_score or 0) >= 75 else "HIGH" if (z.risk_score or 0) >= 60 else "MODERATE" if (z.risk_score or 0) >= 40 else "SAFE",
            })

    db_gates = db.query(Gate).all()
    gates_data = []
    if db_gates:
        for g in db_gates:
            gates_data.append({
                "id": str(g.id),
                "name": g.name,
                "type": g.type.value if hasattr(g.type, "value") else str(g.type),
                "status": g.status.value if hasattr(g.status, "value") else str(g.status),
                "zone_id": str(g.zone_id),
                "capacity_per_min": g.capacity_per_min,
            })

    return {
        "event": event_info,
        "zones": zones_data,
        "gates": gates_data,
    }
