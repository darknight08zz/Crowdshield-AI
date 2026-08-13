import pytest
import uuid
from conftest import TestingSessionLocal
from app.models.zone import Zone
from app.api.v1.operator import get_zone_density_grid

@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_density_grid_calibrated_zone(db_session):
    """Test density grid calculation for calibrated zone."""
    import asyncio
    zone_id = uuid.uuid4()
    zone = Zone(
        id=zone_id,
        event_id=uuid.uuid4(),
        name="Sector A Calibrated",
        capacity=5000,
        current_density=0.70,
        risk_score=78.0,
        calibration_method="homography",
        is_calibrated=1.0,
        area_m2=600.0
    )
    db_session.add(zone)
    db_session.commit()

    res = asyncio.run(get_zone_density_grid(zone_id=str(zone_id), grid_rows=8, grid_cols=8, db=db_session))
    assert res["zone_id"] == str(zone_id)
    assert res["is_calibrated"] is True
    assert res["fallback_to_flat_fill"] is False
    assert res["grid_dims"] == [8, 8]
    assert len(res["grid_densities_peds_m2"]) == 8
    assert len(res["grid_densities_peds_m2"][0]) == 8
    assert res["max_localized_density_peds_m2"] > 0

def test_density_grid_uncalibrated_zone_fallback(db_session):
    """Test density grid graceful degradation for uncalibrated zone."""
    import asyncio
    zone_id = uuid.uuid4()
    zone = Zone(
        id=zone_id,
        event_id=uuid.uuid4(),
        name="Sector B Uncalibrated",
        capacity=5000,
        current_density=0.30,
        risk_score=25.0,
        calibration_method="area_only",
        is_calibrated=0.0,
        area_m2=500.0
    )
    db_session.add(zone)
    db_session.commit()

    res = asyncio.run(get_zone_density_grid(zone_id=str(zone_id), grid_rows=8, grid_cols=8, db=db_session))
    assert res["zone_id"] == str(zone_id)
    assert res["is_calibrated"] is False
    assert res["fallback_to_flat_fill"] is True
    assert res["grid_densities_peds_m2"] is None
    assert "UNCALIBRATED ZONE" in res["warning_banner"]
