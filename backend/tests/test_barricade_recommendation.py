"""
TEST SUITE FOR BARRICADE CONFIGURATION RECOMMENDATION & DISPATCH
================================================================
"""

import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.event import Event
from app.models.zone import Zone
from app.models.gate import Gate, GateStatusEnum, GateTypeEnum
from app.models.barricade import Barricade, BarricadeConfigurationEnum
from app.models.recommendation import AIRecommendation
from app.models.user import User, UserRoleEnum
from app.models.assignment import OfficerAssignment

from app.ai.recommend import generate_recommendations
from app.ai.simulate import simulate_intervention
from app.services.dispatch import dispatch_approved_action

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_barricade_data_model_separation_and_recommendation(db_session):
    """
    Verify Barricade and Gate are distinct models in schema and RECONFIGURE_BARRICADE works in recommend, simulate, & dispatch.
    """
    event_id = uuid.uuid4()
    zone_id = uuid.uuid4()

    event = Event(id=event_id, name="Stadium Fest 2026", date=datetime.utcnow(), venue="Arena", status="active")
    zone = Zone(id=zone_id, event_id=event_id, name="Sector A Choke-Point", capacity=5000, current_density=0.75, risk_score=78.0)
    gate = Gate(id=uuid.uuid4(), event_id=event_id, zone_id=zone_id, name="Gate 1", type=GateTypeEnum.ENTRY, status=GateStatusEnum.OPEN)

    barricade_id = uuid.uuid4()
    barricade = Barricade(
        id=barricade_id,
        event_id=event_id,
        zone_id=zone_id,
        name="Internal Corridor Flow Divider #1",
        current_configuration=BarricadeConfigurationEnum.OPEN,
        moveable=True
    )

    officer_id = uuid.uuid4()
    officer = User(
        id=officer_id,
        email="officer_test@crowdshield.io",
        password_hash="hash",
        name="Officer Davis",
        role=UserRoleEnum.FIELD_OFFICER.value,
        is_active=True
    )

    db_session.add_all([event, zone, gate, barricade, officer])
    db_session.commit()

    # 1. Verify schema independence (Gate vs Barricade tables exist separately)
    assert Barricade.__tablename__ == "barricades"
    assert Gate.__tablename__ == "gates"
    assert barricade.current_configuration == BarricadeConfigurationEnum.OPEN

    # 2. Recommendation Engine Test
    feature_dict = {
        "current_density": 0.75,
        "inflow_rate": 95.0,
        "outflow_rate": 45.0,
        "avg_pedestrian_speed": 0.70,
        "direction_conflict_score": 0.40,
        "recent_incident_count_10min": 1.0,
        "reverse_flow_ratio": 0.10
    }

    recs = generate_recommendations(
        zone_id=zone_id,
        current_risk=78.0,
        predicted_risk_5min=82.0,
        feature_dict=feature_dict,
        db=db_session
    )

    action_types = [r["action_type"] for r in recs]
    assert "RECONFIGURE_BARRICADE" in action_types

    barricade_rec = next(r for r in recs if r["action_type"] == "RECONFIGURE_BARRICADE")
    assert barricade_rec["target_barricade_id"] == str(barricade_id)
    assert barricade_rec["new_configuration"] == "redirect_left"

    # 3. What-If Simulation Test
    sim_result = simulate_intervention(
        zone_id=zone_id,
        proposed_action=barricade_rec,
        db=db_session
    )
    assert sim_result["risk_delta"] < 0  # Reconfiguring barricade lowers projected risk

    # 4. Dispatch Test
    rec_entity = AIRecommendation(
        id=uuid.uuid4(),
        zone_id=zone_id,
        risk_score=78.0,
        predicted_risk_5min=82.0,
        recommended_actions=[barricade_rec],
        status="pending"
    )
    db_session.add(rec_entity)
    db_session.commit()

    dispatch_res = dispatch_approved_action(recommendation_id=rec_entity.id, db=db_session)
    assert len(dispatch_res["actions_executed"]) > 0

    # Verify Barricade status in DB updated
    db_session.refresh(barricade)
    assert barricade.current_configuration == BarricadeConfigurationEnum.REDIRECT_LEFT

    # Verify Field Officer Task assignment created
    assignments = db_session.query(OfficerAssignment).filter(OfficerAssignment.officer_id == officer_id).all()
    assert len(assignments) == 1
    assert "Reconfigure barricade" in assignments[0].task_description
