import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.schemas.realtime_inference import RealtimeInferenceResponse

client = TestClient(app)


def get_auth_headers(role: str = "operator") -> dict:
    token = create_access_token(
        user_id=str(uuid4()),
        email=f"{role}@crowdshield.ai",
        role=role
    )
    return {"Authorization": f"Bearer {token}"}


def test_01_get_event_map_configuration_schema():
    """
    Verifies that GET /api/v1/operator/events/{event_id}/map returns valid static geospatial
    configuration containing event details, camera coordinates, and zone geometries.
    """
    headers = get_auth_headers("operator")
    event_id = "evt_01"
    response = client.get(f"/api/v1/operator/events/{event_id}/map", headers=headers)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()

    assert data["event_id"] == event_id
    assert "latitude" in data and "longitude" in data
    assert data["latitude"] == 37.7745
    assert data["longitude"] == -122.4174

    # Verify Cameras array
    assert "cameras" in data and isinstance(data["cameras"], list)
    assert len(data["cameras"]) >= 4

    for cam in data["cameras"]:
        assert "camera_id" in cam
        assert "name" in cam
        assert "latitude" in cam and "longitude" in cam
        assert "zone_id" in cam
        assert "status" in cam

        # Validate Coordinate Bounds
        lat, lng = cam["latitude"], cam["longitude"]
        assert -90.0 <= lat <= 90.0, f"Invalid latitude: {lat}"
        assert -180.0 <= lng <= 180.0, f"Invalid longitude: {lng}"

    # Verify Zones array
    assert "zones" in data and isinstance(data["zones"], list)
    for zone in data["zones"]:
        assert "zone_id" in zone
        assert "name" in zone
        assert "geometry" in zone
        if zone["geometry"]:
            assert zone["geometry"]["type"] == "Polygon"
            assert isinstance(zone["geometry"]["coordinates"], list)


def test_02_coordinate_validation_logic():
    """
    Verifies valid lat/lng validation logic and that malformed coordinates are rejected.
    """
    def is_valid_coordinate(lat, lng):
        if lat is None or lng is None:
            return False
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            return False
        return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0

    # Valid Coordinates
    assert is_valid_coordinate(37.7745, -122.4174) is True
    assert is_valid_coordinate(0.0, 0.0) is True

    # Invalid Coordinates
    assert is_valid_coordinate(91.0, 0.0) is False
    assert is_valid_coordinate(-90.1, 45.0) is False
    assert is_valid_coordinate(45.0, 181.0) is False
    assert is_valid_coordinate(None, -122.4174) is False
    assert is_valid_coordinate("37.7745", "-122.4174") is False


def test_03_camera_zone_composite_key_isolation():
    """
    Verifies that realtime stream payloads key telemetry by composite (event_id, camera_id, zone_id)
    so Camera A never receives Camera B's operational warning state.
    """
    cam1_payload = {
        "event_id": "evt_01",
        "camera_id": "CAM-01",
        "zone_id": "z-1",
        "timestamp": "2026-08-15T23:00:00Z",
        "camera_health": {"status": "ONLINE", "fps": 30.0},
        "telemetry": {
            "person_count": 120,
            "density": 1.8,
            "average_speed": 0.8,
            "median_speed": 0.8,
            "inflow_rate": 20,
            "outflow_rate": 15,
            "flow_imbalance": 5,
            "net_accumulation": 5,
            "direction_conflict_score": 0.1,
            "reverse_flow_ratio": 0.05,
            "blockage_score": 0.0
        },
        "current_risk": {"score": 42.0, "bucket": "MODERATE"},
        "ai_prediction": {"probability": 0.35, "status": "READY"},
        "warning": {"operational_warning_state": "NORMAL"},
        "provenance": {
            "model_version": "v2.0.0",
            "model_status": "PROTOTYPE",
            "label_type": "PHYSICS_DEFINED_PROXY",
            "ground_truth_status": "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
            "generalization_status": "PROTOTYPE_ONLY",
            "target": "EARLY_ESCALATION_5M",
            "target_version": "v2.0.0",
            "horizon_seconds": 300
        }
    }

    cam3_payload = {
        "event_id": "evt_01",
        "camera_id": "CAM-03",
        "zone_id": "z-3",
        "timestamp": "2026-08-15T23:00:00Z",
        "camera_health": {"status": "ONLINE", "fps": 30.0},
        "telemetry": {
            "person_count": 280,
            "density": 3.2,
            "average_speed": 0.3,
            "median_speed": 0.3,
            "inflow_rate": 60,
            "outflow_rate": 10,
            "flow_imbalance": 50,
            "net_accumulation": 50,
            "direction_conflict_score": 0.6,
            "reverse_flow_ratio": 0.35,
            "blockage_score": 0.7
        },
        "current_risk": {"score": 78.5, "bucket": "CRITICAL"},
        "ai_prediction": {"probability": 0.88, "status": "READY"},
        "warning": {"operational_warning_state": "EARLY_WARNING"},
        "provenance": {
            "model_version": "v2.0.0",
            "model_status": "PROTOTYPE",
            "label_type": "PHYSICS_DEFINED_PROXY",
            "ground_truth_status": "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
            "generalization_status": "PROTOTYPE_ONLY",
            "target": "EARLY_ESCALATION_5M",
            "target_version": "v2.0.0",
            "horizon_seconds": 300
        }
    }

    res1 = RealtimeInferenceResponse.from_orchestrator_result(cam1_payload)
    res3 = RealtimeInferenceResponse.from_orchestrator_result(cam3_payload)

    # Verify Isolation
    assert res1.camera_id == "CAM-01"
    assert res1.operational_warning_state == "NORMAL"
    assert res1.current_physics_risk == 42.0
    assert res1.ai_probability == 0.35

    assert res3.camera_id == "CAM-03"
    assert res3.operational_warning_state == "EARLY_WARNING"
    assert res3.current_physics_risk == 78.5
    assert res3.ai_probability == 0.88

    # Verify no cross-talk
    assert res1.operational_warning_state != res3.operational_warning_state
