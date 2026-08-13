"""
TEST SUITE FOR ANNOUNCEMENT DRAFTING AND RECOMMENDATION EXTENSIONS
===================================================================
"""

import pytest
from app.ai.announce import draft_announcement
from app.ai.recommend import generate_recommendations
from app.ai.simulate import simulate_intervention
from app.ai.behavior import BehaviorType


def test_draft_announcement_english():
    draft = draft_announcement("REVERSE_FLOW", "Sector A", language="en")
    assert "Sector A" in draft
    assert "One-way pedestrian flow is in effect" in draft


def test_draft_announcement_hindi():
    draft = draft_announcement("REVERSE_FLOW", "Sector A", language="hi")
    assert "Sector A" in draft
    assert "एकतरफा पैदल मार्ग नियम लागू है" in draft


def test_draft_announcement_fallback_language():
    draft = draft_announcement("SURGE", "Sector B", language="fr")
    assert "Sector B" in draft
    assert "High crowd density detected" in draft


def test_recommendation_enforce_one_way_flow():
    features = {
        "current_density": 0.65,
        "inflow_rate": 80.0,
        "outflow_rate": 80.0,
        "avg_pedestrian_speed": 1.10,
        "direction_conflict_score": 0.65,
        "gate_capacity_utilization": 0.50,
        "recent_incident_count_10min": 0.0,
        "reverse_flow_ratio": 0.45,
        "blockage_score": 0.10
    }

    # Dummy class for Session
    class MockDB:
        def query(self, model):
            class QueryMock:
                def filter(self, *args, **kwargs):
                    class FilterMock:
                        def all(self):
                            return []
                    return FilterMock()
            return QueryMock()

    recs = generate_recommendations(
        zone_id="00000000-0000-0000-0000-000000000001",
        current_risk=65.0,
        predicted_risk_5min=70.0,
        feature_dict=features,
        db=MockDB()
    )

    action_types = [r["action_type"] for r in recs]
    assert "ENFORCE_ONE_WAY_FLOW" in action_types
    one_way_rec = next(r for r in recs if r["action_type"] == "ENFORCE_ONE_WAY_FLOW")
    assert "route_id" in one_way_rec


def test_simulate_enforce_one_way_flow():
    class MockDB:
        def query(self, model):
            return None

    # Simulate proposed action dict
    proposed = {"action_type": "ENFORCE_ONE_WAY_FLOW"}
    res = simulate_intervention("00000000-0000-0000-0000-000000000001", proposed, db=None)

    assert "risk_delta" in res
    baseline_reverse = res["simulated_feature_changes"]["baseline"]["reverse_flow_ratio"]
    adjusted_reverse = res["simulated_feature_changes"]["adjusted"]["reverse_flow_ratio"]
    assert adjusted_reverse <= baseline_reverse
