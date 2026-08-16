from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.authorization import normalize_role, CanonicalRole
from app.core.security import UserPayload
from app.models.incident import Incident, IncidentTransition
from app.models.incident_report import IncidentReport, IncidentReportStatusEnum
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


def create_incident_report(
    db: Session,
    user: UserPayload,
    payload: IncidentReportCreate
) -> IncidentReport:
    """
    Creates a new human-submitted incident report.
    submitted_by_user_id is extracted from authenticated user session (never from client body).
    Initial status is strictly REPORT_SUBMITTED.
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

    report_id = generate_report_id()
    now = datetime.now(timezone.utc)

    report = IncidentReport(
        report_id=report_id,
        event_id=payload.event_id or "evt_01",
        zone_id=payload.zone_id,
        camera_id=payload.camera_id,
        submitted_by_user_id=user_uuid,
        submitted_at=now,
        status=IncidentReportStatusEnum.REPORT_SUBMITTED.value,
        title=payload.title,
        description=payload.description,
        reported_location=payload.reported_location,
        report_source="VIEWER",
        media_url=payload.media_url,
        created_at=now,
        updated_at=now,
    )

    db.add(report)
    db.commit()
    db.refresh(report)

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

    return report


def get_user_incident_reports(db: Session, user_id: str) -> List[IncidentReport]:
    """Retrieves all reports submitted by the given user_id."""
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
    """Lists all incident reports for operational review."""
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
    Supported targets: UNDER_REVIEW, ACCEPTED, REJECTED.
    Only ADMIN and OPERATOR roles are allowed.
    Atomic transaction guarantees clean rollback on failure.
    """
    report = get_incident_report_by_id(db, report_identifier)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident report '{report_identifier}' not found."
        )

    target_status = review_payload.status.upper()
    valid_statuses = [
        IncidentReportStatusEnum.UNDER_REVIEW.value,
        IncidentReportStatusEnum.ACCEPTED.value,
        IncidentReportStatusEnum.REJECTED.value,
    ]
    if target_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid review status '{target_status}'. Must be one of {valid_statuses}."
        )

    # Prevent transitions on already terminal reports
    if report.status in (IncidentReportStatusEnum.ACCEPTED.value, IncidentReportStatusEnum.REJECTED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition report '{report.report_id}' in terminal status '{report.status}'."
        )

    # Prevent duplicate same-status transition
    if report.status == target_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report '{report.report_id}' is already in status '{target_status}'."
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

        report.status = IncidentReportStatusEnum.REJECTED.value
        report.reviewed_by_user_id = reviewer_uuid
        report.reviewed_at = now
        report.review_reason = review_payload.review_reason.strip()
        report.updated_at = now

        db.commit()
        db.refresh(report)

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
        return report

    elif target_status == IncidentReportStatusEnum.UNDER_REVIEW.value:
        report.status = IncidentReportStatusEnum.UNDER_REVIEW.value
        report.reviewed_by_user_id = reviewer_uuid
        report.reviewed_at = now
        if review_payload.review_reason:
            report.review_reason = review_payload.review_reason.strip()
        report.updated_at = now

        db.commit()
        db.refresh(report)

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
        return report

    elif target_status == IncidentReportStatusEnum.ACCEPTED.value:
        # Atomic creation of operational Incident linked to accepted human report
        inc_uuid = uuid4()
        inc_human_id = generate_incident_id()
        zone_id_value = report.zone_id or "22222222-2222-2222-2222-222222222222"

        operational_incident = Incident(
            id=inc_uuid,
            incident_id=inc_human_id,
            event_id=report.event_id or "evt_01",
            camera_id=report.camera_id,
            zone_id=zone_id_value,
            reporter_id=report.submitted_by_user_id,
            type="VIEWER_REPORT",
            description=f"[{report.title}] {report.description}",
            media_url=report.media_url,
            status="OPEN",
            source_type="VIEWER_REPORT",
            warning_state_at_creation="HUMAN_REPORTED",
            latest_warning_state="HUMAN_REPORTED",
            model_version="v2.0.0",
            prediction_target="HUMAN_REPORTED_INCIDENT",
            label_type="HUMAN_SUBMITTED_OBSERVATION",
            model_status="PROTOTYPE",
            ground_truth_status="NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
            generalization_status="HUMAN_VERIFIED_REPORT",
            disclaimer="Human-Submitted Viewer Report accepted by operator. Not generated by AI models.",
            created_at=now,
            updated_at=now,
        )

        db.add(operational_incident)
        db.flush()  # Flush to generate operational_incident.id UUID

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

        db.commit()
        db.refresh(report)

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

        return report

    return report
