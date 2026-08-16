"""
CROWDSHIELD INCIDENT MANAGEMENT SERVICE (PHASE 6D.1)
=====================================================
Centralized service for evaluating real-time warning states against the Incident
Creation Policy, enforcing deduplication, managing the deterministic state machine,
and recording immutable transition audit logs.
"""

from datetime import datetime, timezone
import logging
import uuid
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.incident import Incident, IncidentTransition
from app.schemas.incident import (
    IncidentCanonicalResponse,
    CreationSnapshot,
    LatestSnapshot,
    IncidentProvenance,
    IncidentTransitionResponse,
)

logger = logging.getLogger("crowdshield.services.incident")

# Deterministic Lifecycle State Transition Matrix
VALID_TRANSITIONS: Dict[str, set] = {
    "OPEN": {"ACKNOWLEDGED", "FALSE_POSITIVE"},
    "ACKNOWLEDGED": {"INVESTIGATING", "FALSE_POSITIVE", "RESOLVED"},
    "INVESTIGATING": {"MITIGATING", "RESOLVED"},
    "MITIGATING": {"RESOLVED"},
    "RESOLVED": set(),  # Terminal state
    "FALSE_POSITIVE": set(),  # Terminal state
}

# Terminal states where incidents are considered closed
TERMINAL_STATES = {"RESOLVED", "FALSE_POSITIVE", "resolved", "false_alarm"}


from app.core.config import settings

def evaluate_incident_policy(
    operational_warning_state: str,
    trigger_states: Optional[List[str]] = None
) -> bool:
    """
    Incident Creation Policy Engine:
    Evaluates whether a real-time operational warning state requires incident tracking.
    This is an operational policy choice (configurable via settings.INCIDENT_POLICY_TRIGGER_STATES)
    rather than a scientifically validated AI ground truth.

    Default policy triggers on: EARLY_WARNING, HIGH_RISK
    Default policy ignores: NORMAL, WATCH
    """
    state_upper = (operational_warning_state or "").upper()
    allowed_triggers = set(s.upper() for s in (trigger_states or getattr(settings, "INCIDENT_POLICY_TRIGGER_STATES", ["EARLY_WARNING", "HIGH_RISK"])))
    return state_upper in allowed_triggers


def generate_incident_id() -> str:
    """Generates a human-readable unique incident ID: INC-YYYYMMDD-XXXX"""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d")
    short_uid = uuid.uuid4().hex[:6].upper()
    return f"INC-{date_str}-{short_uid}"


def process_realtime_inference_incident(db: Session, result_data: Dict[str, Any]) -> Optional[Incident]:
    """
    Evaluates an incoming RealtimeInferenceResult payload against the Incident Creation Policy.
    Uses composite key correlation (event_id, camera_id, zone_id) to update existing active
    incidents or create a new incident without spamming duplicate active records.
    
    Failure-Safe: Wraps DB operations so telemetry ingestion never crashes on DB glitch.
    """
    try:
        event_id = str(result_data.get("event_id", "evt_01"))
        camera_id = result_data.get("camera_id")
        if camera_id is not None:
            camera_id = str(camera_id)
        zone_id = str(result_data.get("zone_id", ""))

        # Extract operational warning state
        warning = result_data.get("warning") or {}
        warn_state = warning.get("operational_warning_state") or result_data.get("operational_warning_state", "NORMAL")

        # Extract risk metrics
        current_risk_obj = result_data.get("current_risk") or {}
        physics_risk = float(current_risk_obj.get("score", current_risk_obj.get("current_risk", result_data.get("current_physics_risk", 0.0))))

        ai_pred_obj = result_data.get("ai_prediction") or {}
        ai_prob = ai_pred_obj.get("probability", result_data.get("ai_probability"))
        if ai_prob is not None:
            ai_prob = float(ai_prob)

        telemetry_ts = result_data.get("telemetry_timestamp") or result_data.get("timestamp")
        prediction_ts = result_data.get("prediction_timestamp") or result_data.get("timestamp")

        cam_health_obj = result_data.get("camera_health") or {}
        cam_health_status = cam_health_obj.get("status", result_data.get("camera_health_status", "ONLINE"))

        is_stale = bool(result_data.get("is_stale", False))
        is_degraded = bool(result_data.get("is_degraded", False))

        # Check for active incident for (event_id, camera_id, zone_id)
        query = db.query(Incident).filter(
            Incident.event_id == event_id,
            Incident.zone_id == zone_id,
            ~Incident.status.in_(list(TERMINAL_STATES))
        )
        if camera_id:
            query = query.filter(Incident.camera_id == camera_id)

        active_incident = query.order_by(Incident.created_at.desc()).first()

        if active_incident:
            # Update latest context on active incident (Deduplication / Correlation)
            active_incident.latest_warning_state = warn_state
            active_incident.latest_physics_risk = physics_risk
            active_incident.latest_ai_probability = ai_prob
            active_incident.latest_telemetry_timestamp = telemetry_ts
            active_incident.camera_health_status = cam_health_status
            active_incident.is_stale = is_stale
            active_incident.is_degraded = is_degraded
            active_incident.updated_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(active_incident)
            logger.info(f"[INCIDENT SERVICE] Updated active incident {active_incident.incident_id} latest context")
            return active_incident

        # If no active incident exists, evaluate policy
        if evaluate_incident_policy(warn_state):
            incident_id = generate_incident_id()
            new_incident = Incident(
                incident_id=incident_id,
                event_id=event_id,
                camera_id=camera_id,
                zone_id=zone_id,
                status="OPEN",
                source_type="AI_EARLY_WARNING_PROXY",
                warning_state_at_creation=warn_state,
                physics_risk_at_creation=physics_risk,
                ai_probability_at_creation=ai_prob,
                telemetry_timestamp=telemetry_ts,
                prediction_timestamp=prediction_ts,
                latest_warning_state=warn_state,
                latest_physics_risk=physics_risk,
                latest_ai_probability=ai_prob,
                latest_telemetry_timestamp=telemetry_ts,
                camera_health_status=cam_health_status,
                is_stale=is_stale,
                is_degraded=is_degraded,
                model_version="v2.0.0",
                prediction_target="EARLY_ESCALATION_5M",
                label_type="PHYSICS_DEFINED_PROXY",
                model_status="PROTOTYPE",
                ground_truth_status="NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
                generalization_status="INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION",
                disclaimer="AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(new_incident)
            db.flush()

            # Record initial SYSTEM transition log
            transition = IncidentTransition(
                transition_id=f"TR-{uuid.uuid4().hex[:8].upper()}",
                incident_id=new_incident.incident_id,
                previous_status="NONE",
                new_status="OPEN",
                timestamp=datetime.now(timezone.utc),
                actor_type="SYSTEM",
                actor_id=None,
                reason=f"Automated creation trigger from operational warning state: {warn_state}",
                metadata_json={
                    "warning_state": warn_state,
                    "physics_risk": physics_risk,
                    "ai_probability": ai_prob,
                }
            )
            db.add(transition)
            db.commit()
            db.refresh(new_incident)
            logger.info(f"[INCIDENT SERVICE] Created new incident {new_incident.incident_id} for zone {zone_id}")
            return new_incident

        return None

    except Exception as e:
        db.rollback()
        logger.error(f"[INCIDENT SERVICE] Persistence error processing realtime incident: {e}", exc_info=True)
        return None


def transition_incident_status(
    db: Session,
    incident_id_or_uuid: str,
    new_status: str,
    actor_id: str,
    reason: Optional[str] = None
) -> Incident:
    """
    Executes a deterministic state machine transition for an incident.
    Validates allowed transitions, records operator identity from auth, and appends
    an immutable audit log entry in IncidentTransition.
    """
    target_status = new_status.upper()

    # Query by incident_id or UUID string safely
    try:
        val_uuid = uuid.UUID(str(incident_id_or_uuid))
        query_filter = or_(Incident.incident_id == incident_id_or_uuid, Incident.id == val_uuid)
    except (ValueError, AttributeError):
        query_filter = (Incident.incident_id == incident_id_or_uuid)

    incident = db.query(Incident).filter(query_filter).first()

    if not incident:
        raise ValueError(f"Incident '{incident_id_or_uuid}' not found.")

    current_status = incident.status.upper()

    if current_status in TERMINAL_STATES:
        raise ValueError(f"Cannot transition incident '{incident.incident_id}' from terminal state '{current_status}'.")

    allowed = VALID_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise ValueError(f"Invalid state transition from '{current_status}' to '{target_status}'. Allowed transitions: {sorted(list(allowed))}")

    # Execute State Transition
    previous_status = incident.status
    incident.status = target_status
    incident.updated_at = datetime.now(timezone.utc)

    if target_status == "ACKNOWLEDGED":
        incident.acknowledged_by = actor_id
        incident.acknowledged_at = datetime.now(timezone.utc)
    elif target_status in {"RESOLVED", "FALSE_POSITIVE"}:
        incident.resolved_by = actor_id
        incident.resolved_at = datetime.now(timezone.utc)
        incident.resolution_type = target_status
        incident.resolution_notes = reason

    # Create Audit Log Record
    transition = IncidentTransition(
        transition_id=f"TR-{uuid.uuid4().hex[:8].upper()}",
        incident_id=incident.incident_id,
        previous_status=previous_status,
        new_status=target_status,
        timestamp=datetime.now(timezone.utc),
        actor_type="OPERATOR",
        actor_id=actor_id,
        reason=reason,
        metadata_json={
            "previous_status": previous_status,
            "new_status": target_status,
            "actor_id": actor_id,
        }
    )
    db.add(transition)
    db.commit()
    db.refresh(incident)
    logger.info(f"[INCIDENT SERVICE] Transitioned incident {incident.incident_id}: {previous_status} -> {target_status} by operator {actor_id}")
    return incident


def format_canonical_incident_response(incident: Incident) -> IncidentCanonicalResponse:
    """Helper to convert Incident DB model into canonical schema structure."""
    creation_snapshot = CreationSnapshot(
        source_type=incident.source_type or "AI_EARLY_WARNING_PROXY",
        warning_state_at_creation=incident.warning_state_at_creation or "EARLY_WARNING",
        physics_risk_at_creation=incident.physics_risk_at_creation,
        ai_probability_at_creation=incident.ai_probability_at_creation,
        telemetry_timestamp=incident.telemetry_timestamp,
        prediction_timestamp=incident.prediction_timestamp,
    )

    latest_snapshot = LatestSnapshot(
        latest_warning_state=incident.latest_warning_state or incident.warning_state_at_creation,
        latest_physics_risk=incident.latest_physics_risk if incident.latest_physics_risk is not None else incident.physics_risk_at_creation,
        latest_ai_probability=incident.latest_ai_probability if incident.latest_ai_probability is not None else incident.ai_probability_at_creation,
        latest_telemetry_timestamp=incident.latest_telemetry_timestamp or incident.telemetry_timestamp,
    )

    provenance = IncidentProvenance(
        model_version=incident.model_version or "v2.0.0",
        prediction_target=incident.prediction_target or "EARLY_ESCALATION_5M",
        label_type=incident.label_type or "PHYSICS_DEFINED_PROXY",
        model_status=incident.model_status or "PROTOTYPE",
        ground_truth_status=incident.ground_truth_status or "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
        generalization_status=incident.generalization_status or "INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION",
        disclaimer=incident.disclaimer or "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.",
    )

    transition_responses = [
        IncidentTransitionResponse(
            transition_id=t.transition_id,
            incident_id=t.incident_id,
            previous_status=t.previous_status,
            new_status=t.new_status,
            timestamp=t.timestamp,
            actor_type=t.actor_type,
            actor_id=t.actor_id,
            reason=t.reason,
            metadata_json=t.metadata_json,
        )
        for t in (incident.transitions or [])
    ]

    return IncidentCanonicalResponse(
        incident_id=incident.incident_id,
        event_id=incident.event_id,
        camera_id=incident.camera_id,
        zone_id=incident.zone_id,
        status=incident.status,
        source_type=incident.source_type,
        creation_snapshot=creation_snapshot,
        latest_snapshot=latest_snapshot,
        camera_health_status=incident.camera_health_status or "ONLINE",
        is_stale=bool(incident.is_stale),
        is_degraded=bool(incident.is_degraded),
        provenance=provenance,
        acknowledged_by=incident.acknowledged_by,
        acknowledged_at=incident.acknowledged_at,
        resolved_by=incident.resolved_by,
        resolved_at=incident.resolved_at,
        resolution_type=incident.resolution_type,
        resolution_notes=incident.resolution_notes,
        transitions=transition_responses,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
    )
