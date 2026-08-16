"""
CROWDSHIELD PHASE 6H DEPLOYMENT & INFRASTRUCTURE TEST SUITE
============================================================
Tests native deployment configuration, health probes, readiness diagnostics,
request correlation headers, asynchronous persistence metrics, and graceful shutdown semantics.
"""

import pytest
import os
import threading
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import Settings, settings
from app.services.async_persistence import AsyncPersistenceManager, PersistenceEventType, EventPriority

client = TestClient(app)


def test_health_endpoint():
    """
    Verifies that root and API health endpoints return 200 OK liveness indicator.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "healthy"]
    assert "service" in data
    assert "version" in data
    assert "environment" in data

    api_response = client.get("/api/v1/health")
    assert api_response.status_code == 200


def test_readiness_endpoint():
    """
    Verifies that the /readiness endpoint evaluates database, persistence, AI, and camera health.
    Validates explicit AI provenance disclaimers.
    """
    response = client.get("/readiness")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ["READY", "DEGRADED"]
    assert data["database"] in ["CONNECTED", "UNAVAILABLE"]
    assert data["persistence"] in ["RUNNING", "DEGRADED"]
    assert data["ai_model"] in ["READY", "DEGRADED"]

    # Verify AI Provenance & Disclaimer Fields
    ai_details = data["details"]["ai_model"]
    assert ai_details["model_version"] == "v2.0.0"
    assert ai_details["model_status"] == "PROTOTYPE"
    assert ai_details["label_type"] == "PHYSICS_DEFINED_PROXY"
    assert ai_details["ground_truth_status"] == "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED"

    # Verify Persistence Diagnostics Fields
    p_details = data["details"]["persistence"]
    assert "queue_depth" in p_details
    assert "queue_capacity" in p_details
    assert "active_workers" in p_details


def test_request_id_correlation():
    """
    Verifies that X-Request-ID headers are preserved or generated and returned in response.
    """
    # 1. Custom Request ID preserved
    custom_id = "req_phase6h_test_12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id

    # 2. Generated Request ID if header omitted
    gen_response = client.get("/health")
    assert gen_response.status_code == 200
    assert "X-Request-ID" in gen_response.headers
    assert len(gen_response.headers["X-Request-ID"]) > 0


def test_production_environment_validation():
    """
    Verifies fail-fast behavior when invalid configuration is passed for production environment.
    """
    insecure_settings = Settings(
        ENV="production",
        DEBUG=True,
        DATABASE_URL="postgresql://postgres:postgres@localhost:5432/postgres",
        SUPABASE_JWT_SECRET=""
    )

    with pytest.raises(ValueError) as exc_info:
        insecure_settings.validate_production_config()

    error_msg = str(exc_info.value)
    assert "DEBUG mode must be False in production" in error_msg
    assert "SUPABASE_JWT_SECRET must be set" in error_msg


def test_async_persistence_manager_diagnostics():
    """
    Verifies AsyncPersistenceManager diagnostic metric extraction.
    """
    mgr = AsyncPersistenceManager.get_instance()
    diag = mgr.get_diagnostics()

    assert "status" in diag
    assert "queue_depth" in diag
    assert "queue_maxsize" in diag
    assert "num_workers" in diag
    assert diag["queue_depth"] >= 0
    assert diag["num_workers"] > 0


def test_graceful_shutdown_semantics():
    """
    Verifies that AsyncPersistenceManager cleanly drains remaining work and stops worker threads during shutdown.
    """
    test_mgr = AsyncPersistenceManager(maxsize=20, num_workers=1)
    processed_items = []

    def test_handler(session, payload):
        processed_items.append(payload["id"])

    # Enqueue tasks
    for i in range(5):
        test_mgr.enqueue_task(
            event_type=PersistenceEventType.AUDIT_LOG,
            payload={"id": i},
            priority=EventPriority.NORMAL,
            handler=test_handler
        )

    # Shutdown with timeout
    test_mgr.shutdown(timeout=3.0)

    # Verify workers drained queue and stopped
    assert len(processed_items) == 5
    assert not test_mgr._is_started
    for worker in test_mgr._workers:
        assert not worker.is_alive()
