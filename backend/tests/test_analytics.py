import pytest
import uuid
import asyncio
from datetime import datetime, timedelta
from conftest import TestingSessionLocal
from app.models import Event, Zone, ZoneMetricsHistory, AIRecommendation
from app.api.v1.analytics import (
    record_zone_metric_snapshot,
    get_zone_trends,
    get_event_analytics_summary,
    export_post_event_report
)

@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_record_zone_metric_snapshot(db_session):
    """Test persisting a zone metric snapshot to zone_metrics_history."""
    event_id = uuid.uuid4()
    zone_id = uuid.uuid4()

    snapshot = record_zone_metric_snapshot(
        db=db_session,
        event_id=event_id,
        zone_id=zone_id,
        density=0.85,
        inflow_rate=55.0,
        outflow_rate=30.0,
        avg_speed=0.9,
        risk_score=82.5,
        behavior_classification="REVERSE_FLOW",
        propagated_risk_score=15.0
    )

    assert snapshot.id is not None
    assert snapshot.event_id == event_id
    assert snapshot.zone_id == zone_id
    assert snapshot.density == 0.85
    assert snapshot.risk_score == 82.5
    assert snapshot.behavior_classification == "REVERSE_FLOW"

def test_get_zone_trends_api(db_session):
    """Test get_zone_trends returning time-series points and derived stats."""
    event_id = uuid.uuid4()
    zone_id = uuid.uuid4()

    event = Event(id=event_id, name="Test Analytics Festival", venue="Stadium", date=datetime.utcnow(), status="active")
    zone = Zone(id=zone_id, event_id=event_id, name="Main Stage Sector", capacity=5000, current_density=0.8, risk_score=80.0)
    db_session.add(event)
    db_session.add(zone)
    db_session.commit()

    # Seed two snapshots: s1 (MODERATE: 35.0) -> s2 (CRITICAL: 85.0)
    s1 = ZoneMetricsHistory(event_id=event_id, zone_id=zone_id, timestamp=datetime.utcnow() - timedelta(minutes=15), density=0.4, risk_score=35.0)
    s2 = ZoneMetricsHistory(event_id=event_id, zone_id=zone_id, timestamp=datetime.utcnow() - timedelta(minutes=5), density=0.9, risk_score=85.0)
    db_session.add(s1)
    db_session.add(s2)
    db_session.commit()

    res = asyncio.run(get_zone_trends(event_id=event_id, zone_id=str(zone_id), hours=1, db=db_session))
    assert res["event_id"] == str(event_id)
    assert res["zone_id"] == str(zone_id)
    assert len(res["snapshots"]) >= 2
    assert res["derived_stats"]["peak_risk_score"] == 85.0
    assert res["derived_stats"]["escalation_count"] >= 1

def test_get_event_analytics_summary_and_report(db_session):
    """Test event-wide summary aggregation and executive report generation."""
    event_id = uuid.uuid4()
    zone_id = uuid.uuid4()

    event = Event(id=event_id, name="Executive Safety Summit", venue="Main Arena", date=datetime.utcnow(), status="active")
    zone = Zone(id=zone_id, event_id=event_id, name="VVIP Enclosure", capacity=2000, current_density=0.85, risk_score=78.0)
    db_session.add(event)
    db_session.add(zone)

    rec = AIRecommendation(
        id=uuid.uuid4(),
        zone_id=zone_id,
        risk_score=78.0,
        predicted_risk_5min=85.0,
        recommended_actions=[{"title": "Restrict Entry Gate"}],
        status="approved"
    )
    db_session.add(rec)
    db_session.commit()


    summary = asyncio.run(get_event_analytics_summary(event_id=event_id, db=db_session))
    assert summary["event_id"] == str(event_id)
    assert len(summary["zones_ranked_by_elevated_risk"]) >= 1
    assert len(summary["intervention_effectiveness"]) >= 1
    assert summary["intervention_success_rate_pct"] > 0

    report = asyncio.run(export_post_event_report(event_id=event_id, db=db_session))
    assert "CROWDSHIELD EXECUTIVE SAFETY REPORT" in report["title"]
    assert report["key_metrics"]["safety_verdict"] == "PASSED — ZERO CRITICAL STAMPEDE INCIDENTS"
