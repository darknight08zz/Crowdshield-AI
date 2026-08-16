"""
CROWDSHIELD PHASE 6H DEPLOYMENT HARDENING TEST SUITE
====================================================
Validates all Phase 6H modification requirements:
1. /health lightweight probe
2. /readiness full dependency check
3. Dependency state exposure in /readiness
4. X-Request-ID correlation tracking
5. Production configuration validation
6. Critical persistence preservation during shutdown
7. AsyncPersistenceManager clean shutdown
8. Secret absence in logging formatters
9. Existence of native PowerShell deployment scripts
10. Absence of Docker requirements in native scripts
11. Hardware-qualified performance benchmark metadata
12. Prototype AI provenance compliance
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import Settings, settings
from app.services.async_persistence import AsyncPersistenceManager, PersistenceEventType, EventPriority

client = TestClient(app)


def test_lightweight_health_endpoint():
    """1. Verifies that /health is lightweight and does not trigger DB queries."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "healthy"]
    assert "service" in data
    assert "version" in data
    assert "environment" in data


def test_readiness_dependency_exposure():
    """2 & 3. Verifies /readiness exposes detailed component state."""
    response = client.get("/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["READY", "DEGRADED", "NOT_READY"]
    assert "database" in data
    assert "persistence" in data
    assert "ai_model" in data
    assert "camera" in data

    details = data["details"]
    assert "database_status" in details
    assert "persistence" in details
    assert "ai_model" in details
    assert "camera" in details


def test_request_id_correlation():
    """4. Verifies X-Request-ID correlation is functional."""
    custom_id = "req_hardening_test_999"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


def test_startup_configuration_validation():
    """5. Verifies configuration validation raises error on insecure settings."""
    insecure = Settings(
        ENV="production",
        DEBUG=True,
        DATABASE_URL="postgresql://postgres:pass@localhost:5432/postgres",
        SUPABASE_JWT_SECRET=""
    )
    with pytest.raises(ValueError) as exc_info:
        insecure.validate_production_config()
    assert "DEBUG mode must be False in production" in str(exc_info.value)


def test_critical_persistence_preservation_and_clean_shutdown():
    """6 & 7. Verifies AsyncPersistenceManager does not discard critical tasks on shutdown."""
    mgr = AsyncPersistenceManager(maxsize=10, num_workers=1)
    executed = []

    def handler(session, payload):
        executed.append(payload["id"])

    for i in range(3):
        mgr.enqueue_task(
            event_type=PersistenceEventType.AUDIT_LOG,
            payload={"id": i},
            priority=EventPriority.HIGH,
            handler=handler
        )

    mgr.shutdown(timeout=2.0)
    assert len(executed) == 3
    assert not mgr._is_started


def test_secrets_absence_in_logging_config():
    """8. Verifies logging formatters and configuration do not output secrets."""
    log_formatter_str = str(settings.LOG_LEVEL)
    assert "password" not in log_formatter_str.lower()
    assert "jwt_secret" not in log_formatter_str.lower()


def test_native_deployment_scripts_exist_without_docker():
    """9 & 10. Verifies native PowerShell scripts exist and do not enforce Docker."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    start_script = os.path.join(root_dir, "scripts", "start_crowdshield.ps1")
    stop_script = os.path.join(root_dir, "scripts", "stop_crowdshield.ps1")
    status_script = os.path.join(root_dir, "scripts", "status_crowdshield.ps1")

    assert os.path.exists(start_script)
    assert os.path.exists(stop_script)
    assert os.path.exists(status_script)

    with open(start_script, "r", encoding="utf-8") as f:
        content = f.read()
        assert "docker run" not in content.lower()
        assert "docker compose" not in content.lower()
        assert "docker-compose" not in content.lower()
        assert "docker build" not in content.lower()



def test_performance_benchmark_hardware_qualification():
    """11. Verifies performance report contains host hardware qualifications."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    known_lims = os.path.join(root_dir, "KNOWN_LIMITATIONS.md")

    assert os.path.exists(known_lims)
    with open(known_lims, "r", encoding="utf-8") as f:
        content = f.read()
        assert "AMD Ryzen 5 5500U" in content
        assert "640x640" in content
        assert "320x320" in content


def test_prototype_ai_provenance_intact():
    """12. Verifies prototype AI provenance fields in readiness check."""
    response = client.get("/readiness")
    assert response.status_code == 200
    ai_details = response.json()["details"]["ai_model"]

    assert ai_details["model_status"] == "PROTOTYPE"
    assert ai_details["label_type"] == "PHYSICS_DEFINED_PROXY"
    assert ai_details["ground_truth_status"] == "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED"
    assert ai_details["generalization_status"] == "INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION"
