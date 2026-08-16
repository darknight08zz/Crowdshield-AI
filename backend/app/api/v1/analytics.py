from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.database import get_db
from app.core.security import require_role, UserPayload
from app.models import Event, Zone, AIRecommendation, AuditLog, ZoneMetricsHistory
from app.core.risk_levels import get_risk_bucket, RiskBucket

router = APIRouter(prefix="/events/{event_id}/analytics", tags=["Analytics & Historical Trends"])


def record_zone_metric_snapshot(
    db: Session,
    event_id: UUID,
    zone_id: UUID,
    density: float,
    inflow_rate: float,
    outflow_rate: float,
    avg_speed: float,
    risk_score: float,
    behavior_classification: str = "NORMAL",
    propagated_risk_score: float = 0.0
) -> ZoneMetricsHistory:
    """
    Persists a time-series metric snapshot for a zone.
    """
    snapshot = ZoneMetricsHistory(
        event_id=event_id,
        zone_id=zone_id,
        timestamp=datetime.utcnow(),
        density=density,
        inflow_rate=inflow_rate,
        outflow_rate=outflow_rate,
        avg_speed=avg_speed,
        risk_score=risk_score,
        behavior_classification=behavior_classification,
        propagated_risk_score=propagated_risk_score
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.get(
    "/zone-trends",
    dependencies=[Depends(require_role("operator", "event_admin", "system_admin", "field_officer"))]
)
async def get_zone_trends(
    event_id: UUID,
    zone_id: Optional[str] = Query(None, description="Optional zone ID filter"),
    hours: int = Query(1, ge=1, le=168, description="Time window in hours (default: 1 hour)"),
    db: Session = Depends(get_db)
):
    """
    Returns time-series metrics (risk score, density %, inflow/outflow velocity) and derived stats for charting.
    Allowed roles: operator, event_admin, system_admin, field_officer
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(ZoneMetricsHistory).filter(
        ZoneMetricsHistory.event_id == event_id,
        ZoneMetricsHistory.timestamp >= start_time
    )

    if zone_id:
        try:
            target_zone_uuid = UUID(zone_id)
            query = query.filter(ZoneMetricsHistory.zone_id == target_zone_uuid)
        except ValueError:
            pass

    snapshots = query.order_by(ZoneMetricsHistory.timestamp.asc()).all()

    # Derived Statistics Calculation from actual timestamps
    peak_risk_score = 0.0
    peak_risk_timestamp = None
    sustained_critical_seconds = 0.0
    escalation_count = 0
    prev_bucket = None

    for i, s in enumerate(snapshots):
        if s.risk_score > peak_risk_score:
            peak_risk_score = s.risk_score
            peak_risk_timestamp = s.timestamp.isoformat()

        if i > 0:
            delta_sec = (s.timestamp - snapshots[i-1].timestamp).total_seconds()
            if delta_sec <= 900.0 and snapshots[i-1].risk_score >= 75.0:
                sustained_critical_seconds += delta_sec

        curr_bucket = get_risk_bucket(s.risk_score)
        if prev_bucket in [RiskBucket.LOW, RiskBucket.MODERATE] and curr_bucket in [RiskBucket.HIGH, RiskBucket.CRITICAL]:
            escalation_count += 1
        prev_bucket = curr_bucket

    formatted_snapshots = [
        {
            "id": str(s.id),
            "zone_id": str(s.zone_id),
            "timestamp": s.timestamp.isoformat(),
            "risk_score": s.risk_score,
            "risk_bucket": get_risk_bucket(s.risk_score).value,
            "density": s.density,
            "density_pct": round(s.density * 100.0, 1),
            "inflow_rate": s.inflow_rate,
            "outflow_rate": s.outflow_rate,
            "avg_speed": s.avg_speed,
            "behavior_classification": s.behavior_classification,
            "propagated_risk_score": s.propagated_risk_score or 0.0
        } for s in snapshots
    ]

    return {
        "event_id": str(event_id),
        "zone_id": zone_id,
        "time_window_hours": hours,
        "total_snapshots": len(formatted_snapshots),
        "derived_stats": {
            "peak_risk_score": round(peak_risk_score, 1),
            "peak_risk_timestamp": peak_risk_timestamp,
            "sustained_critical_minutes": round(sustained_critical_seconds / 60.0, 1),
            "escalation_count": escalation_count,
            "average_risk_score": round(sum(s["risk_score"] for s in formatted_snapshots) / max(1, len(formatted_snapshots)), 1)
        },
        "snapshots": formatted_snapshots
    }


@router.get(
    "/summary",
    dependencies=[Depends(require_role("operator", "event_admin", "system_admin"))]
)
async def get_event_analytics_summary(
    event_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Returns event-wide analytics: zones ranked by elevated risk duration and projected intervention metrics.
    Allowed roles: operator, event_admin, system_admin
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    zones = db.query(Zone).filter(Zone.event_id == event_id).all()
    if not zones:
        zones = db.query(Zone).all()

    # 1. Elevated Risk Duration per Zone (calculated from actual timestamps)
    zone_summaries = []
    for zone in zones:
        history = db.query(ZoneMetricsHistory).filter(
            ZoneMetricsHistory.zone_id == zone.id
        ).order_by(ZoneMetricsHistory.timestamp.asc()).all()

        elevated_seconds = 0.0
        for i in range(1, len(history)):
            prev_h = history[i-1]
            curr_h = history[i]
            delta_sec = (curr_h.timestamp - prev_h.timestamp).total_seconds()
            if delta_sec <= 900.0 and prev_h.risk_score >= 50.0:
                elevated_seconds += delta_sec

        peak_risk = max([h.risk_score for h in history] + [zone.risk_score or 0.0])

        zone_summaries.append({
            "zone_id": str(zone.id),
            "zone_name": zone.name,
            "capacity": zone.capacity,
            "current_risk_score": zone.risk_score,
            "peak_risk_score": round(peak_risk, 1),
            "elevated_risk_minutes": round(elevated_seconds / 60.0, 1),
            "risk_bucket": get_risk_bucket(zone.risk_score or 0.0).value
        })

    zone_summaries.sort(key=lambda x: x["elevated_risk_minutes"], reverse=True)

    # 2. Intervention Effectiveness Analysis (Explicit projected simulation semantics)
    approved_recs = db.query(AIRecommendation).filter(
        AIRecommendation.status == "approved"
    ).all()

    interventions = []
    total_projected_reduction_pts = 0.0

    for rec in approved_recs:
        before_risk = float(rec.risk_score or 75.0)
        projected_after_risk = max(15.0, round(before_risk * 0.65, 1))
        projected_delta = round(before_risk - projected_after_risk, 1)
        pct_reduction = round((projected_delta / before_risk) * 100.0, 1)

        if projected_delta > 0:
            total_projected_reduction_pts += projected_delta

        action_title = "Barricade Reconfiguration & Gate Restriction"
        if rec.recommended_actions and len(rec.recommended_actions) > 0:
            action_title = rec.recommended_actions[0].get("title", action_title)

        interventions.append({
            "recommendation_id": str(rec.id),
            "action_title": action_title,
            "approved_at": rec.created_at.isoformat() if rec.created_at else datetime.utcnow().isoformat(),
            "before_risk_score": before_risk,
            "projected_after_risk_score": projected_after_risk,
            "projected_risk_reduction_points": projected_delta,
            "projected_risk_reduction_pct": pct_reduction,
            "intervention_status": "APPROVED",
            "outcome_type": "PROJECTED",
            "outcome_verdict": "PROJECTED_MITIGATION"
        })

    return {
        "event_id": str(event_id),
        "event_name": event.name if event else "Active Event",
        "total_monitored_zones": len(zones),
        "total_approved_interventions": len(interventions),
        "outcome_semantics": "PROJECTED_SIMULATION",
        "average_projected_risk_reduction_pts": round(total_projected_reduction_pts / max(1, len(interventions)), 1) if interventions else 0.0,
        "zones_ranked_by_elevated_risk": zone_summaries,
        "intervention_effectiveness": interventions
    }


@router.get(
    "/export-report",
    dependencies=[Depends(require_role("event_admin", "system_admin", "operator"))]
)
async def export_post_event_report(
    event_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Generates post-event crowd safety summary report for authorities & oversight bodies.
    Allowed roles: event_admin, system_admin, operator
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    summary = await get_event_analytics_summary(event_id=event_id, db=db)

    report_content = {
        "title": f"CROWDSHIELD EVENT SAFETY SUMMARY: {event.name if event else 'Stadium Fest 2026'}",
        "generated_at": datetime.utcnow().isoformat(),
        "prepared_for": "Event Security Authority & Public Safety Oversight Board",
        "executive_summary": (
            f"During '{event.name if event else 'Stadium Fest 2026'}', CrowdShield monitored {summary['total_monitored_zones']} operational sectors. "
            f"The Risk Engine evaluated real-time crowd dynamics, logging {summary['total_approved_interventions']} operator-approved intervention recommendations. "
            f"What-if simulation models project an average risk score reduction of {summary['average_projected_risk_reduction_pts']} points per intervention. "
            f"Note: Observed telemetry outcomes require live post-event telemetry validation."
        ),
        "key_metrics": {
            "total_sectors_monitored": summary["total_monitored_zones"],
            "interventions_logged": summary["total_approved_interventions"],
            "avg_projected_risk_reduction": f"-{summary['average_projected_risk_reduction_pts']} pts",
            "evaluation_status": "PROTOTYPE_SIMULATION_EVALUATION"
        },
        "sector_risk_rankings": summary["zones_ranked_by_elevated_risk"],
        "intervention_audit_trail": summary["intervention_effectiveness"],
        "disclaimer": "This report contains projected simulation metrics. Observed outcomes require post-event field telemetry validation."
    }

    return report_content

