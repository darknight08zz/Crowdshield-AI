"""
CROWDSHIELD AI PIPELINE END-TO-END SUITE
========================================
Pytest suite verifying feature extraction, XGBoost risk prediction,
Explainable AI (XAI), recommendation engine, and what-if simulation.
"""

import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from datetime import datetime
from app.core.database import Base
from app.models import Event, Zone, Gate, Incident
from app.ai.features import FEATURE_NAMES, extract_zone_features, simulate_sensor_reading
from app.ai.risk_model import predict_risk
from app.ai.explain import explain_risk_score
from app.ai.recommend import generate_recommendations
from app.ai.simulate import simulate_intervention


# In-memory SQLite database setup for automated testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Seed test zone, event, and gate
    event_id = uuid.uuid4()
    zone_id = uuid.uuid4()
    gate_id = uuid.uuid4()

    event = Event(id=event_id, name="Test Festival", date=datetime.utcnow(), venue="Arena", status="active")
    zone = Zone(id=zone_id, event_id=event_id, name="Test Zone", capacity=5000, current_density=0.82, risk_score=0.75)
    gate = Gate(id=gate_id, event_id=event_id, zone_id=zone_id, name="Emergency Exit 1", type="emergency", capacity_per_min=200, status="closed")

    db.add(event)
    db.add(zone)
    db.add(gate)
    db.commit()

    yield db, zone_id

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_feature_extraction(db_session):
    db, zone_id = db_session
    features = extract_zone_features(zone_id=zone_id, db=db)

    assert isinstance(features, dict)
    for name in FEATURE_NAMES:
        assert name in features
        assert isinstance(features[name], float)


def test_risk_prediction(db_session):
    db, zone_id = db_session
    features = extract_zone_features(zone_id=zone_id, db=db)
    risk_dict = predict_risk(features)

    assert isinstance(risk_dict, dict)
    assert "current_risk" in risk_dict
    assert "risk_2min" in risk_dict
    assert "risk_5min" in risk_dict
    assert "risk_10min" in risk_dict
    assert 0.0 <= risk_dict["current_risk"] <= 100.0
    assert 0.0 <= risk_dict["risk_5min"] <= 100.0


def test_explainable_ai(db_session):
    db, zone_id = db_session
    features = extract_zone_features(zone_id=zone_id, db=db)
    risk_dict = predict_risk(features)

    explanation = explain_risk_score(current_risk=risk_dict["current_risk"], feature_dict=features, risk_trajectory=risk_dict)

    assert "summary" in explanation
    assert len(explanation["summary"]) > 10
    assert "top_risk_factors" in explanation
    assert "trajectory_trend" in explanation


def test_recommendation_engine(db_session):
    db, zone_id = db_session
    features = extract_zone_features(zone_id=zone_id, db=db)
    risk_dict = predict_risk(features)

    recs = generate_recommendations(
        zone_id=zone_id,
        current_risk=risk_dict["current_risk"],
        predicted_risk_5min=risk_dict["risk_5min"],
        feature_dict=features,
        db=db,
        risk_trajectory=risk_dict
    )

    assert isinstance(recs, list)
    assert len(recs) > 0
    assert "action_type" in recs[0]


def test_what_if_simulation(db_session):
    db, zone_id = db_session
    proposed_action = {"action_type": "OPEN_EMERGENCY_GATE"}
    
    sim_result = simulate_intervention(zone_id=zone_id, proposed_action=proposed_action, db=db)

    assert "baseline_risk" in sim_result
    assert "projected_risk_after" in sim_result
    assert "risk_delta" in sim_result
    assert sim_result["risk_delta"] <= 0  # Opening exit gate should lower or maintain risk score
