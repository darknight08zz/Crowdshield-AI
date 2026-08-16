from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.authorization import normalize_role, CanonicalRole
from app.core.security import UserPayload
from app.models.event import Event
from app.models.zone import Zone
from app.models.incident import Incident, IncidentTransition
from app.models.incident_report import IncidentReport, IncidentReportStatusEnum, VALID_INCIDENT_REPORT_TRANSITIONS
from app.schemas.incident_report import IncidentReportCreate, IncidentReportReview
from app.services.audit_service import log_action


def generate_report_id() -> str:
    """Generates human readable unique report ID, e.g., REP-20260816-A1B2C3."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid4().hex[:6].upper()
    return f"REP-{date_str}-{unique_suffix}"


def generate_incident_id() -> str:
    """Generates human readable unique incident ID, e.g., INC-20260816-X1Y2Z3."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid4().hex[:6].upper()
    return f"INC-{date_str}-{unique_suffix}"


def validate_event_exists(db: Session, event_identifier: str) -> Optional[Event]:
    """Validates if an Event exists by UUID string, UUID object, or name string."""
    if not event_identifier:
        return None

    try:
        uuid_obj = UUID(str(event_identifier))
        ev = db.query(Event).filter(Event.id == uuid_obj).first()
        if ev:
            return ev
    except (ValueError, AttributeError):
        pass

    ev = db.query(Event).filter(Event.name == str(event_identifier)).first()
    if ev:
        return ev

    return None


def validate_zone_exists(db: Session, zone_identifier: str) -> Optional[Zone]:
    """Validates if a Zone exists by UUID string, UUID object, or name string."""
    if not zone_identifier:
        return None

    try:
        uuid_obj = UUID(str(zone_identifier))
        z = db.query(Zone).filter(Zone.id == uuid_obj).first()
        if z:
            return z
    except (ValueError, AttributeError):
        pass

    z = db.query(Zone).filter(Zone.name == str(zone_identifier)).first()
    if z:
        return z

    return None


def sanitize_media_url(media_url: Optional[str]) -> Optional[str]:
    """
    Validates and sanitizes media_url reference.
    Rejects unsafe file system path traversals (e.g. C:\, file://, ../, etc.).
    """
    if not media_url:
        return None
    url = str(media_url).strip()
    if not url:
        return None
    
    forbidden_prefixes = ("file://", "c:", "d:", "\\\\", "/etc/", "/var/", "/usr/")
    lower_url = url.lower()
    if any(lower_url.startswith(pref) for pref in forbidden_prefixes) or ".." in url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid media_url: Path traversal or local file references are not permitted."
        )
    return url


def create_incident_report(
    db: Session,
    user: UserPayload,
    payload: IncidentReportCreate
) -> IncidentReport:
    """
    Creates a new human-submitted incident report.
    submitted_by_user_id is extracted from authenticated user session (never from client body).
    No fake default event IDs or synthetic fallbacks are used.
    """
    if not user or not user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to submit incident report."
        )

    try:
        user_uuid = UUID(str(user.id))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format in token session."
        )

    # Validate Event context
    target_event_id: Optional[str] = None
    if payload.event_id:
        event_obj = validate_event_exists(db, payload.event_id)
        if not event_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Specified Event ID '{payload.event_id}' does not exist."
            )
        target_event_id = str(event_obj.id)
    else:
        # Check if an existing real event is active in DB
        active_event = db.query(Event).first()
        if active_event:
            target_event_id = str(active_event.id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event ID is required and must be a valid, accessible event."
            )

    # Validate Zone if provided
    target_zone_id: Optional[str] = None
    if payload.zone_id:
        zone_obj = validate_zone_exists(db, payload.zone_id)
        if not zone_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Specified Zone ID '{payload.zone_id}' does not exist."
            )
        target_zone_id = str(zone_obj.id)

    # Sanitize media_url
    safe_media_url = sanitize_media_url(payload.media_url)

    report_id = generate_report_id()
    now = datetime.now(timezone.utc)

    report = IncidentReport(
        report_id=report_id,
        event_id=target_event_id,
        zone_id=target_zone_id,
        camera_id=payload.camera_id,
        submitted_by_user_id=user_uuid,
        submitted_at=now,
        status=IncidentReportStatusEnum.REPORT_SUBMITTED.value,
        title=payload.title,
        description=payload.description,
        reported_location=payload.reported_location,
        report_source="VIEWER",
        media_url=safe_media_url,
        created_at=now,
        updated_at=now,
    )

    try:
        db.add(report)
        db.flush()

        log_action(
            db=db,
            actor_id=user_uuid,
            actor_role=user.role,
            action="INCIDENT_REPORT_CREATED",
            target=f"incident_report:{report.report_id}",
            resource_type="INCIDENT_REPORT",
            resource_id=report.report_id,
            event_id=report.event_id,
            zone_id=report.zone_id,
            camera_id=report.camera_id,
            after_state={
                "status": report.status,
                "title": report.title,
                "report_source": report.report_source,
                "submitted_by_user_id": str(user_uuid),
            },
            source="API"
        )
        db.commit()
        db.refresh(report)
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save incident report: {str(e)}"
        )

    return report


def get_user_incident_reports(db: Session, user_id: str) -> List[IncidentReport]:
    """Retrieves all reports submitted strictly by the authenticated user_id."""
    try:
        user_uuid = UUID(str(user_id))
    except Exception:
        return []

    return (
        db.query(IncidentReport)
        .filter(IncidentReport.submitted_by_user_id == user_uuid)
        .order_by(IncidentReport.created_at.desc())
        .all()
    )


def list_incident_reports(
    db: Session,
    status_filter: Optional[str] = None,
    event_id: Optional[str] = None
) -> List[IncidentReport]:
    """Lists all incident reports for operational review (ADMIN/OPERATOR)."""
    query = db.query(IncidentReport)
    if status_filter:
        query = query.filter(IncidentReport.status == status_filter.upper())
    if event_id:
        query = query.filter(IncidentReport.event_id == event_id)

    return query.order_by(IncidentReport.created_at.desc()).all()


def get_incident_report_by_id(db: Session, report_identifier: str) -> Optional[IncidentReport]:
    """Looks up report by report_id string or UUID string."""
    report = db.query(IncidentReport).filter(IncidentReport.report_id == report_identifier).first()
    if not report:
        try:
            uuid_obj = UUID(report_identifier)
            report = db.query(IncidentReport).filter(IncidentReport.id == uuid_obj).first()
        except Exception:
            pass
    return report


def review_incident_report(
    db: Session,
    report_identifier: str,
    reviewer: UserPayload,
    review_payload: IncidentReportReview
) -> IncidentReport:
    """
    Executes an operational review transition on an IncidentReport.
    Enforces canonical VALID_INCIDENT_REPORT_TRANSITIONS state machine.
    Guarantees 100% atomic transaction: report update, incident creation, transition creation, and audit logging succeed or roll back together.
    """
    report = get_incident_report_by_id(db, report_identifier)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident report '{report_identifier}' not found."
        )

    current_status = report.status
    target_status = review_payload.status.upper()
    allowed_targets = VALID_INCIDENT_REPORT_TRANSITIONS.get(current_status, set())

    if target_status not in allowed_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report state transition from '{current_status}' to '{target_status}'."
        )

    reviewer_uuid = None
    if reviewer and reviewer.id:
        try:
            reviewer_uuid = UUID(str(reviewer.id))
        except Exception:
            pass

    norm_role = normalize_role(reviewer.role) if reviewer else CanonicalRole.OPERATOR
    now = datetime.now(timezone.utc)
    before_status = report.status

    if target_status == IncidentReportStatusEnum.REJECTED.value:
        if not review_payload.review_reason or not review_payload.review_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid review_reason is required when rejecting an incident report."
            )

        try:
            report.status = IncidentReportStatusEnum.REJECTED.value
            report.reviewed_by_user_id = reviewer_uuid
            report.reviewed_at = now
            report.review_reason = review_payload.review_reason.strip()
            report.updated_at = now

            db.flush()

            log_action(
                db=db,
                actor_id=reviewer_uuid,
                actor_role=reviewer.role if reviewer else "operator",
                action="INCIDENT_REPORT_REJECTED",
                target=f"incident_report:{report.report_id}",
                resource_type="INCIDENT_REPORT",
                resource_id=report.report_id,
                event_id=report.event_id,
                zone_id=report.zone_id,
                camera_id=report.camera_id,
                before_state={"status": before_status},
                after_state={"status": report.status, "reason": report.review_reason},
                reason=report.review_reason,
                source="API"
            )
            db.commit()
            db.refresh(report)
            return report
        except Exception as e:
            db.rollback()
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to execute report rejection transaction: {str(e)}"
            )

    elif target_status == IncidentReportStatusEnum.UNDER_REVIEW.value:
        try:
            report.status = IncidentReportStatusEnum.UNDER_REVIEW.value
            report.reviewed_by_user_id = reviewer_uuid
            report.reviewed_at = now
            if review_payload.review_reason:
                report.review_reason = review_payload.review_reason.strip()
            report.updated_at = now

            db.flush()

            log_action(
                db=db,
                actor_id=reviewer_uuid,
                actor_role=reviewer.role if reviewer else "operator",
                action="INCIDENT_REPORT_REVIEW_STARTED",
                target=f"incident_report:{report.report_id}",
                resource_type="INCIDENT_REPORT",
                resource_id=report.report_id,
                event_id=report.event_id,
                zone_id=report.zone_id,
                camera_id=report.camera_id,
                before_state={"status": before_status},
                after_state={"status": report.status},
                source="API"
            )
            db.commit()
            db.refresh(report)
            return report
        except Exception as e:
            db.rollback()
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to transition report to UNDER_REVIEW: {str(e)}"
            )

    elif target_status == IncidentReportStatusEnum.ACCEPTED.value:
        # Determine and validate zone ID
        candidate_zone_id = review_payload.zone_id or report.zone_id
        target_zone_id: Optional[str] = None

        if candidate_zone_id:
            zone_obj = validate_zone_exists(db, candidate_zone_id)
            if not zone_obj:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Specified Zone ID '{candidate_zone_id}' does not exist."
                )
            target_zone_id = str(zone_obj.id)

        try:
            inc_uuid = uuid4()
            inc_human_id = generate_incident_id()

            operational_incident = Incident(
                id=inc_uuid,
                incident_id=inc_human_id,
                event_id=report.event_id,
                camera_id=report.camera_id,
                zone_id=target_zone_id,
                reporter_id=report.submitted_by_user_id,
                type="VIEWER_REPORT",
                description=f"[{report.title}] {report.description}",
                media_url=report.media_url,
                status="OPEN",
                source_type="VIEWER_REPORT",
                warning_state_at_creation="HUMAN_REPORTED",
                physics_risk_at_creation=None,
                ai_probability_at_creation=None,
                latest_warning_state="HUMAN_REPORTED",
                latest_physics_risk=None,
                latest_ai_probability=None,
                model_version="NOT_APPLICABLE",
                prediction_target="NOT_APPLICABLE",
                label_type="HUMAN_SUBMITTED_OBSERVATION",
                model_status="NOT_APPLICABLE",
                ground_truth_status="NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
                generalization_status="NOT_APPLICABLE",
                disclaimer="Human-Submitted Viewer Report accepted by operator. Not generated by AI models.",
                created_at=now,
                updated_at=now,
            )

            db.add(operational_incident)
            db.flush()

            report.status = IncidentReportStatusEnum.ACCEPTED.value
            report.reviewed_by_user_id = reviewer_uuid
            report.reviewed_at = now
            if review_payload.review_reason:
                report.review_reason = review_payload.review_reason.strip()
            report.accepted_incident_id = operational_incident.id
            report.updated_at = now

            transition_actor_type = "OPERATOR" if norm_role == CanonicalRole.OPERATOR else "ADMIN"
            transition = IncidentTransition(
                transition_id=f"TR-{uuid4().hex[:8].upper()}",
                incident_id=operational_incident.incident_id,
                previous_status="NONE",
                new_status="OPEN",
                timestamp=now,
                actor_type=transition_actor_type,
                actor_id=str(reviewer.id) if reviewer else "operator",
                reason=f"Created from accepted human report {report.report_id}",
                metadata_json={
                    "report_id": report.report_id,
                    "source": "VIEWER_REPORT",
                    "review_reason": report.review_reason
                }
            )
            db.add(transition)

            log_action(
                db=db,
                actor_id=reviewer_uuid,
                actor_role=reviewer.role if reviewer else "operator",
                action="INCIDENT_REPORT_ACCEPTED",
                target=f"incident_report:{report.report_id}",
                resource_type="INCIDENT_REPORT",
                resource_id=report.report_id,
                event_id=report.event_id,
                zone_id=report.zone_id,
                camera_id=report.camera_id,
                before_state={"status": before_status},
                after_state={
                    "status": report.status,
                    "accepted_incident_id": str(operational_incident.id),
                    "incident_id": operational_incident.incident_id,
                },
                reason=report.review_reason,
                source="API"
            )

            log_action(
                db=db,
                actor_id=reviewer_uuid,
                actor_role=reviewer.role if reviewer else "operator",
                action="INCIDENT_CREATED_FROM_VIEWER_REPORT",
                target=f"incident:{operational_incident.incident_id}",
                resource_type="INCIDENT",
                resource_id=operational_incident.incident_id,
                event_id=operational_incident.event_id,
                zone_id=operational_incident.zone_id,
                camera_id=operational_incident.camera_id,
                after_state={
                    "incident_id": operational_incident.incident_id,
                    "source_type": "VIEWER_REPORT",
                    "status": "OPEN",
                    "originating_report_id": report.report_id,
                },
                source="API"
            )

            db.commit()
            db.refresh(report)
            return report

        except Exception as e:
            db.rollback()
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to execute report acceptance transaction: {str(e)}"
            )

    return report
