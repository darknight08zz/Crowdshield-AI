"""
TEST SUITE FOR PANIC PROPAGATION MODELING & ZONE ADJACENCY GRAPH
=================================================================
"""

import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.event import Event
from app.models.zone import Zone
from app.models.zone_adjacency import ZoneAdjacency, ConnectionType
from app.ai.propagation import calculate_zone_propagation, infer_default_adjacencies

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


def test_zone_adjacency_graph_and_panic_propagation(db_session):
    """
    Worked example demonstrating one zone's rising risk visibly propagating into a defined neighbor.
    - Zone A (Main Stage): High density & current risk (~85.0)
    - Zone B (North Exit Promenade): Low baseline density & risk (~20.0)
    - Connected via Gate 1 with high capacity.
    """
    # 1. Setup Event and Zones
    event_id = uuid.uuid4()
    event = Event(id=event_id, name="Fest 2026 Test Event", date=datetime.utcnow(), venue="Test Stadium", status="active")
    db_session.add(event)

    zone_a_id = uuid.uuid4()
    zone_b_id = uuid.uuid4()

    zone_a = Zone(
        id=zone_a_id,
        event_id=event_id,
        name="Sector A (Main Stage)",
        capacity=10000,
        current_density=0.88,
        risk_score=85.0
    )
    zone_b = Zone(
        id=zone_b_id,
        event_id=event_id,
        name="Sector B (North Promenade)",
        capacity=5000,
        current_density=0.25,
        risk_score=20.0
    )

    db_session.add_all([zone_a, zone_b])
    db_session.commit()

    # 2. Configure Zone Adjacency (Gate 1 connection)
    adj = ZoneAdjacency(
        event_id=event_id,
        zone_a_id=zone_a_id,
        zone_b_id=zone_b_id,
        connection_type=ConnectionType.GATE,
        connection_capacity=150.0,
        vector_direction="bidirectional"
    )
    db_session.add(adj)
    db_session.commit()

    # 3. Execute Propagation Physics Calculation
    propagation_graph = calculate_zone_propagation(event_id=event_id, db=db_session)

    # 4. Verify Zone B (Downstream Neighbor) Risk Source & Bleed
    assert str(zone_b_id) in propagation_graph
    prop_b = propagation_graph[str(zone_b_id)]

    assert prop_b["risk_source"].startswith("propagated_from:")
    assert prop_b["propagated_from_zone_id"] == str(zone_a_id)
    assert prop_b["propagated_from_zone_name"] == "Sector A (Main Stage)"
    assert len(prop_b["incoming_contributions"]) > 0

    top_contrib = prop_b["incoming_contributions"][0]
    assert top_contrib["source_zone_name"] == "Sector A (Main Stage)"
    assert top_contrib["connection_type"] == "gate"
    assert top_contrib["risk_contribution"] > 15.0

    assert "Risk incoming from Sector A (Main Stage)" in prop_b["explanation_line"]
    assert "Gate" in prop_b["explanation_line"]
