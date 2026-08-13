from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.security import require_role, UserPayload
from app.models import Event, Zone, Gate, Incident, AIRecommendation, OfficerAssignment, ZoneAdjacency, Barricade
from app.schemas.recommendation import AIRecommendationResponse, AIRecommendationAction
from app.schemas.gate import GateResponse, GateStatusUpdate
from app.schemas.assignment import OfficerAssignmentCreate, OfficerAssignmentResponse
from app.schemas.zone import ZoneAdjacencyCreate, ZoneAdjacencyResponse
from app.schemas.barricade import BarricadeResponse, BarricadeCreate, BarricadeConfigUpdate
from app.services.audit_service import log_action

from app.ai.features import extract_zone_features, SAFE_BASELINES
from app.ai.risk_model import predict_risk
from app.ai.behavior import classify_behavior
from app.ai.explain import explain_risk_score
from app.ai.recommend import generate_recommendations
from app.ai.simulate import simulate_intervention
from app.ai.announce import draft_announcement
from app.ai.propagation import calculate_zone_propagation
from app.services.dispatch import dispatch_approved_action
from app.core.risk_levels import get_risk_bucket, evaluate_multi_horizon_risk, RiskBucket

router = APIRouter(prefix="/operator", tags=["Control Room Operator"])


@router.get(
    "/dashboard",
    dependencies=[Depends(require_role("operator", "event_admin", "system_admin"))]
)
async def get_control_room_dashboard(db: Session = Depends(get_db)):
    """
    Returns unified real-time snapshot of events, zones, gates, incidents, and pending AI recommendations.
    Allowed roles: operator, event_admin, system_admin
    """
    events = db.query(Event).all()
    zones = db.query(Zone).all()
    gates = db.query(Gate).all()
    active_incidents = db.query(Incident).filter(Incident.status.in_(["reported", "verified"])).all()
    pending_recommendations = db.query(AIRecommendation).filter(AIRecommendation.status == "pending").all()
    active_assignments = db.query(OfficerAssignment).filter(OfficerAssignment.status.in_(["assigned", "in_progress"])).all()
    adjacencies = db.query(ZoneAdjacency).all()

    return {
        "events": events,
        "zones": zones,
        "gates": gates,
        "active_incidents": active_incidents,
        "pending_recommendations": pending_recommendations,
        "active_assignments": active_assignments,
        "adjacencies": adjacencies
    }


def is_valid_uuid(val: Any) -> bool:
    if not val:
        return False
    try:
        UUID(str(val))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


# ==========================================
# PHASE 2: AI RISK ENGINE ENDPOINTS
# ==========================================

@router.get(
    "/zones/{zone_id}/risk",
    dependencies=[Depends(require_role("operator", "event_admin", "system_admin", "field_officer", "citizen"))]
)
async def get_zone_risk(
    zone_id: str,
    db: Session = Depends(get_db)
):
    """
    Evaluates current risk, 2m / 5m / 10m multi-horizon trajectory prediction, behavior pattern, explainable AI summary, and panic propagation for a zone.
    Allowed roles: ALL authenticated roles
    """
    zone = db.query(Zone).filter(Zone.id == UUID(zone_id)).first() if is_valid_uuid(zone_id) else None
    zone_name = zone.name if zone else f"Sector ({zone_id})"
    event_id = zone.event_id if zone else None

    features_with_meta = extract_zone_features(zone_id=zone_id, db=db, include_metadata=True)
    risk_traj = predict_risk(features_with_meta)
    current_risk = risk_traj["current_risk"]
    risk_2min = risk_traj["risk_2min"]
    risk_5min = risk_traj["risk_5min"]
    risk_10min = risk_traj["risk_10min"]

    mh_eval = evaluate_multi_horizon_risk(current_risk, risk_2min, risk_5min, risk_10min)

    behavior = classify_behavior(features_with_meta)
    explanation = explain_risk_score(current_risk=current_risk, feature_dict=features_with_meta, behavior=behavior, risk_trajectory=risk_traj)

    # Panic Propagation Modeling (Prompt 1)
    propagation_data = None
    risk_source = "independent"
    propagated_from_zone_id = None
    propagated_from_zone_name = None

    if event_id:
        prop_res = calculate_zone_propagation(event_id=event_id, db=db, target_zone_id=zone.id if zone else None)
        if isinstance(prop_res, dict) and "risk_source" in prop_res:
            propagation_data = prop_res
            risk_source = prop_res.get("risk_source", "independent")
            propagated_from_zone_id = prop_res.get("propagated_from_zone_id")
            propagated_from_zone_name = prop_res.get("propagated_from_zone_name")

    # Time-Series Retention Snapshot
    if zone and event_id:
        try:
            from app.api.v1.analytics import record_zone_metric_snapshot
            record_zone_metric_snapshot(
                db=db,
                event_id=event_id,
                zone_id=zone.id,
                density=features_with_meta.get("current_density", 0.0),
                inflow_rate=features_with_meta.get("inflow_rate", 0.0),
                outflow_rate=features_with_meta.get("outflow_rate", 0.0),
                avg_speed=features_with_meta.get("avg_pedestrian_speed", 1.2),
                risk_score=current_risk,
                behavior_classification=behavior.value,
                propagated_risk_score=propagation_data.get("propagated_risk_score", 0.0) if propagation_data else 0.0
            )
        except Exception:
            pass

    is_degraded = features_with_meta.get("is_degraded", False)
    confidence = features_with_meta.get("confidence_score", 0.85)
    warning_banner = None
    if is_degraded or confidence < 0.50:
        warning_banner = f"⚠️ DEGRADED TELEMETRY ALERT: Real-time sensor stream for Zone {zone_name} is stale or offline. YOU ARE NOW RELYING ON MANUAL JUDGMENT FOR THIS ZONE."


    return {
        "zone_id": str(zone_id),
        "zone_name": zone_name,
        "current_risk_score": current_risk,
        "predicted_risk_2min": risk_2min,
        "predicted_risk_5min": risk_5min,
        "predicted_risk_10min": risk_10min,
        "risk_bucket": mh_eval["current_bucket"],
        "effective_risk_bucket": mh_eval["effective_bucket"],
        "risk_source": risk_source,
        "propagated_from_zone_id": propagated_from_zone_id,
        "propagated_from_zone_name": propagated_from_zone_name,
        "is_escalating": mh_eval["is_escalating"],
        "trajectory_warning": mh_eval["trajectory_warning"],
        "trajectory_trend": explanation.get("trajectory_trend", "STABLE"),
        "behavior_classification": behavior.value,
        "explanation": explanation["summary"],
        "propagation": propagation_data,
        "top_risk_factors": explanation["top_risk_factors"],
        "confidence_score": confidence,
        "telemetry_source": features_with_meta.get("telemetry_source", "synthetic_fallback"),
        "is_degraded": is_degraded,
        "warning_banner": warning_banner,
        "features": {k: v for k, v in features_with_meta.items() if k in SAFE_BASELINES}
    }


@router.get(
    "/events/{event_id}/adjacencies",
    dependencies=[Depends(require_role("operator", "event_admin", "system_admin"))]
)
async def get_event_adjacencies(
    event_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Returns spatial zone adjacencies and propagation graph for an event.
    Allowed roles: operator, event_admin, system_admin
    """
    propagation_graph = calculate_zone_propagation(event_id=event_id, db=db)
    adjacencies = db.query(ZoneAdjacency).filter(ZoneAdjacency.event_id == event_id).all()
    return {
        "event_id": str(event_id),
        "adjacencies": adjacencies,
        "propagation_graph": propagation_graph
    }


@router.get(
    "/zones/{zone_id}/density-grid",
    dependencies=[Depends(require_role("operator", "event_admin", "system_admin", "field_officer", "citizen"))]
)
async def get_zone_density_grid(
    zone_id: str,
    grid_rows: int = Query(10, ge=2, le=20),
    grid_cols: int = Query(10, ge=2, le=20),
    db: Session = Depends(get_db)
):
    """
    Returns spatial sub-zone grid-cell density matrix (peds/m²) and risk gradients for calibrated zones.
    Degrades gracefully to flat fill indicator when homography calibration is unavailable.
    Allowed roles: ALL authenticated roles
    """
    import math

    zone = db.query(Zone).filter(Zone.id == UUID(zone_id)).first() if is_valid_uuid(zone_id) else None
    
    zone_name = zone.name if zone else f"Sector ({zone_id})"
    area_m2 = float(getattr(zone, "area_m2", 500.0)) if zone else 500.0
    current_density = float(getattr(zone, "current_density", 0.5)) if zone else 0.5
    calib_method = getattr(zone, "calibration_method", "area_only") if zone else "area_only"
    is_calibrated_val = float(getattr(zone, "is_calibrated", 0.0)) if zone else 0.0
    
    # Homography calibration check
    is_calibrated = (calib_method == "homography") and (is_calibrated_val > 0.0)

    if not is_calibrated:
        return {
            "zone_id": str(zone_id),
            "zone_name": zone_name,
            "calibration_method": calib_method,
            "is_calibrated": False,
            "fallback_to_flat_fill": True,
            "grid_dims": [grid_rows, grid_cols],
            "average_density_peds_m2": round(current_density * 4.0, 2),
            "max_localized_density_peds_m2": round(current_density * 4.0, 2),
            "grid_densities_peds_m2": None,
            "grid_risk_scores": None,
            "warning_banner": f"UNCALIBRATED ZONE: {zone_name} uses area-only metric mapping. Sub-zone continuous density gradient unavailable. Falling back to flat zone-color fill."
        }

    # Calibrated Homography Subgrid Matrix Generation (Smooth Gaussian spatial gradient)
    cell_w_m = math.sqrt(area_m2) / float(grid_cols)
    cell_h_m = math.sqrt(area_m2) / float(grid_rows)
    cell_area_m2 = max(1.0, cell_w_m * cell_h_m)

    avg_peds_m2 = max(0.2, current_density * 4.0)
    base_risk = zone.risk_score if (zone and zone.risk_score) else (current_density * 100.0)

    # Hotspot center for spatial variance (simulating bottleneck / gate entrance in grid)
    center_r = (grid_rows - 1) * 0.45
    center_c = (grid_cols - 1) * 0.55

    densities: List[List[float]] = []
    risks: List[List[float]] = []
    max_dens = 0.0

    for r in range(grid_rows):
        row_dens: List[float] = []
        row_risk: List[float] = []
        for c in range(grid_cols):
            dist = math.sqrt((r - center_r) ** 2 + (c - center_c) ** 2)
            decay = math.exp(-0.18 * (dist ** 1.5))
            
            cell_dens = round(max(0.1, avg_peds_m2 * (0.4 + 1.2 * decay)), 2)
            cell_risk = round(min(100.0, max(5.0, base_risk * (0.5 + 0.8 * decay))), 1)

            if cell_dens > max_dens:
                max_dens = cell_dens

            row_dens.append(cell_dens)
            row_risk.append(cell_risk)

        densities.append(row_dens)
        risks.append(row_risk)

    return {
        "zone_id": str(zone_id),
        "zone_name": zone_name,
        "calibration_method": "homography",
        "is_calibrated": True,
        "fallback_to_flat_fill": False,
        "grid_dims": [grid_rows, grid_cols],
        "cell_width_meters": round(cell_w_m, 2),
        "cell_height_meters": round(cell_h_m, 2),
        "average_density_peds_m2": round(avg_peds_m2, 2),
        "max_localized_density_peds_m2": max_dens,
        "grid_densities_peds_m2": densities,
        "grid_risk_scores": risks,
        "warning_banner": None
    }




@router.get(
    "/zones/{zone_id}/recommendation",
    dependencies=[Depends(require_role("operator", "event_admin", "system_admin"))]
)
async def get_zone_recommendation(
    zone_id: str,
    lang: Optional[str] = Query("en", description="Language code for public announcement drafting (en/hi)"),
    db: Session = Depends(get_db)
):
    """
    Generates ranked interpretable action recommendations for a specific zone with optional announcement drafting.
    Allowed roles: operator, event_admin, system_admin
    """
    zone = db.query(Zone).filter(Zone.id == UUID(zone_id)).first() if is_valid_uuid(zone_id) else None
    zone_name = zone.name if zone else f"Sector ({zone_id})"

    features = extract_zone_features(zone_id=zone_id, db=db)
    risk_traj = predict_risk(features)
    current_risk = risk_traj["current_risk"]
    risk_5min = risk_traj["risk_5min"]
    behavior = classify_behavior(features)

    recommendations = generate_recommendations(
        zone_id=zone_id,
        current_risk=current_risk,
        predicted_risk_5min=risk_5min,
        feature_dict=features,
        db=db,
        risk_trajectory=risk_traj
    )

    drafted_announcement = draft_announcement(
        situation_type=behavior.value,
        zone_name=zone_name,
        language=lang or "en"
    )

    # Attach draft to recommendations that involve public announcements or advisories
    for rec in recommendations:
        if rec.get("action_type") in ["ISSUE_PUBLIC_ANNOUNCEMENT", "ISSUE_CITIZEN_REROUTE_ALERT"]:
            rec["drafted_announcement"] = drafted_announcement

    return {
        "zone_id": str(zone_id),
        "zone_name": zone_name,
        "current_risk": current_risk,
        "predicted_risk_2min": risk_traj["risk_2min"],
        "predicted_risk_5min": risk_traj["risk_5min"],
        "predicted_risk_10min": risk_traj["risk_10min"],
        "behavior_classification": behavior.value,
        "language": lang or "en",
        "drafted_announcement": drafted_announcement,
        "recommended_actions": recommendations
    }


from app.core.rate_limit import simulate_rate_limiter


@router.post(
    "/zones/{zone_id}/simulate",
    dependencies=[
        Depends(require_role("operator", "event_admin", "system_admin")),
        Depends(simulate_rate_limiter)
    ]
)
async def run_what_if_simulation(
    zone_id: str,
    proposed_action: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Runs what-if simulation for a proposed intervention action and calculates projected risk delta.
    Allowed roles: operator, event_admin, system_admin
    """
    simulation_result = simulate_intervention(
        zone_id=zone_id,
        proposed_action=proposed_action,
        db=db
    )

    return simulation_result


@router.post(
    "/recommendations/{recommendation_id}/decide",
    response_model=AIRecommendationResponse,
    dependencies=[Depends(require_role("operator", "system_admin"))]
)
async def decide_recommendation(
    recommendation_id: UUID,
    decision_payload: AIRecommendationAction,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("operator", "system_admin"))
):
    """
    Approve, Modify, or Reject an AI recommendation.
    Writes decision and original vs edited announcement text to audit log.
    Allowed roles: operator, system_admin
    """
    recommendation = db.query(AIRecommendation).filter(AIRecommendation.id == recommendation_id).first()
    if not recommendation:
        raise HTTPException(status_code=404, detail="AI Recommendation not found.")

    before_status = recommendation.status
    recommendation.status = decision_payload.status
    db.commit()
    db.refresh(recommendation)

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if current_user.id else None,
        action="OPERATOR_DECISION_RECOMMENDATION",
        target=f"recommendation:{recommendation.id}",
        before_state={"status": str(before_status)},
        after_state={
            "status": str(decision_payload.status),
            "original_draft_announcement": decision_payload.original_draft_announcement,
            "edited_announcement": decision_payload.edited_announcement,
            "final_approved_announcement": decision_payload.edited_announcement or decision_payload.original_draft_announcement,
            "was_edited": bool(decision_payload.edited_announcement and decision_payload.edited_announcement != decision_payload.original_draft_announcement)
        }
    )

    if decision_payload.status == "approved":
        dispatch_approved_action(
            recommendation_id=recommendation.id,
            db=db,
            actor_id=UUID(current_user.id) if current_user.id else None
        )

    return recommendation


# ==========================================
# DISPATCH & GATE CONTROLS
# ==========================================

@router.post(
    "/dispatch",
    response_model=OfficerAssignmentResponse,
    dependencies=[Depends(require_role("operator", "event_admin", "system_admin"))]
)
async def dispatch_officer(
    payload: OfficerAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("operator", "event_admin", "system_admin"))
):
    """
    Dispatches a field officer task to manage crowd surge or incident response.
    Allowed roles: operator, event_admin, system_admin
    """
    assignment = OfficerAssignment(
        officer_id=payload.officer_id,
        zone_id=payload.zone_id,
        task_description=payload.task_description,
        status="assigned"
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if current_user.id else None,
        action="DISPATCH_OFFICER",
        target=f"assignment:{assignment.id}",
        after_state={
            "officer_id": str(payload.officer_id),
            "zone_id": str(payload.zone_id),
            "task": payload.task_description
        }
    )

    return assignment


@router.patch(
    "/gates/{gate_id}/status",
    response_model=GateResponse,
    dependencies=[Depends(require_role("operator", "event_admin", "system_admin"))]
)
async def update_gate_status(
    gate_id: UUID,
    payload: GateStatusUpdate,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("operator", "event_admin", "system_admin"))
):
    """
    Manual gate override (e.g. restrict entry, open emergency exit).
    Allowed roles: operator, event_admin, system_admin
    """
    gate = db.query(Gate).filter(Gate.id == gate_id).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found.")

    before_status = gate.status
    gate.status = payload.status
    db.commit()
    db.refresh(gate)

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if current_user.id else None,
        action="OVERRIDE_GATE_STATUS",
        target=f"gate:{gate.id}",
        before_state={"status": str(before_status)},
        after_state={"status": str(payload.status)}
    )

    return gate


@router.get(
    "/events/{event_id}/barricades",
    response_model=List[BarricadeResponse],
    dependencies=[Depends(require_role("operator", "event_admin", "system_admin"))]
)
async def list_event_barricades(
    event_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieves all barricades for a specific event.
    """
    return db.query(Barricade).filter(Barricade.event_id == event_id).all()


@router.post(
    "/barricades",
    response_model=BarricadeResponse,
    dependencies=[Depends(require_role("event_admin", "system_admin"))]
)
async def create_barricade(
    payload: BarricadeCreate,
    db: Session = Depends(get_db)
):
    """
    Admin configuration: add a new physical barricade entity to a zone.
    """
    barricade = Barricade(
        event_id=payload.event_id,
        zone_id=payload.zone_id,
        name=payload.name,
        position_geometry=payload.position_geometry,
        current_configuration=payload.current_configuration,
        moveable=payload.moveable
    )
    db.add(barricade)
    db.commit()
    db.refresh(barricade)
    return barricade


@router.patch(
    "/barricades/{barricade_id}/reconfigure",
    response_model=BarricadeResponse,
    dependencies=[Depends(require_role("operator", "event_admin", "system_admin"))]
)
async def reconfigure_barricade_status(
    barricade_id: UUID,
    payload: BarricadeConfigUpdate,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role("operator", "event_admin", "system_admin"))
):
    """
    Reconfigures a physical barricade (e.g. open, narrow, closed, redirect_left, redirect_right).
    Allowed roles: operator, event_admin, system_admin
    """
    barricade = db.query(Barricade).filter(Barricade.id == barricade_id).first()
    if not barricade:
        raise HTTPException(status_code=404, detail="Barricade not found.")

    before_config = barricade.current_configuration
    barricade.current_configuration = payload.current_configuration
    db.commit()
    db.refresh(barricade)

    log_action(
        db=db,
        actor_id=UUID(current_user.id) if current_user.id else None,
        action="RECONFIGURE_BARRICADE",
        target=f"barricade:{barricade.id}",
        before_state={"configuration": str(before_config)},
        after_state={"configuration": str(payload.current_configuration)}
    )

    return barricade
