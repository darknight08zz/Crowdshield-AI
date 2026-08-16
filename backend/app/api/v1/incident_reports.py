from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, UserPayload
from app.core.authorization import require_canonical_role, CanonicalRole
from app.schemas.incident_report import (
    IncidentReportCreate,
    IncidentReportReview,
    IncidentReportResponse,
)
from app.services.incident_report_service import (
    create_incident_report,
    get_user_incident_reports,
    list_incident_reports,
    get_incident_report_by_id,
    review_incident_report,
)

router = APIRouter(prefix="", tags=["Incident Reports"])


@router.post(
    "/incident-reports",
    response_model=IncidentReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Human Incident Report",
    description="Submits an incident report. Allowed for Viewer, Operator, Admin, and authenticated users. The submitted_by identity comes strictly from the session token."
)
async def submit_incident_report_endpoint(
    payload: IncidentReportCreate,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(get_current_user)
):
    """
    POST /api/v1/incident-reports
    Enforces that VIEWER can submit a report.
    """
    report = create_incident_report(db=db, user=current_user, payload=payload)
    return report


@router.get(
    "/incident-reports/my",
    response_model=List[IncidentReportResponse],
    summary="List My Submitted Incident Reports",
    description="Retrieves incident reports submitted by the currently authenticated user."
)
async def get_my_incident_reports_endpoint(
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(get_current_user)
):
    """
    GET /api/v1/incident-reports/my
    Returns only reports submitted by the authenticated user.
    """
    reports = get_user_incident_reports(db=db, user_id=current_user.id)
    return reports


@router.get(
    "/operator/incident-reports",
    response_model=List[IncidentReportResponse],
    summary="List Pending/Submitted Incident Reports for Operator Review",
    description="Retrieves submitted incident reports for operational review. Only accessible to ADMIN and OPERATOR."
)
async def list_operator_incident_reports_endpoint(
    status: Optional[str] = Query(None, description="Optional status filter: REPORT_SUBMITTED, UNDER_REVIEW, ACCEPTED, REJECTED"),
    event_id: Optional[str] = Query(None, description="Optional event ID filter"),
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_canonical_role(CanonicalRole.ADMIN, CanonicalRole.OPERATOR))
):
    """
    GET /api/v1/operator/incident-reports
    Fails closed with 403 Forbidden for VIEWER and FIELD_OFFICER.
    """
    reports = list_incident_reports(db=db, status_filter=status, event_id=event_id)
    return reports


@router.get(
    "/operator/incident-reports/{report_id}",
    response_model=IncidentReportResponse,
    summary="Get Incident Report Details for Review",
    description="Retrieves details of a specific incident report. Only accessible to ADMIN and OPERATOR."
)
async def get_operator_incident_report_detail_endpoint(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_canonical_role(CanonicalRole.ADMIN, CanonicalRole.OPERATOR))
):
    """
    GET /api/v1/operator/incident-reports/{report_id}
    Fails closed with 403 Forbidden for VIEWER and FIELD_OFFICER.
    """
    report = get_incident_report_by_id(db=db, report_identifier=report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident report '{report_id}' not found."
        )
    return report


@router.post(
    "/operator/incident-reports/{report_id}/review",
    response_model=IncidentReportResponse,
    summary="Review Incident Report (Under Review / Accept / Reject)",
    description="Executes a review action on a submitted incident report. Accepting creates an operational Incident."
)
async def review_operator_incident_report_endpoint(
    report_id: str,
    payload: IncidentReportReview,
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_canonical_role(CanonicalRole.ADMIN, CanonicalRole.OPERATOR))
):
    """
    POST /api/v1/operator/incident-reports/{report_id}/review
    Only accessible to ADMIN and OPERATOR.
    Fails closed with 403 Forbidden for VIEWER and FIELD_OFFICER.
    """
    report = review_incident_report(
        db=db,
        report_identifier=report_id,
        reviewer=current_user,
        review_payload=payload
    )
    return report
