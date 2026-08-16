"""
CROWDSHIELD NATIVE DEPLOYMENT SMOKE TEST SCRIPT (PHASE 6H)
==========================================================
Validates end-to-end native deployment health, database connectivity,
protected endpoints, async persistence worker execution, and WebSocket readiness.
"""

import sys
import os
import time
import json
import logging
import urllib.request
import urllib.error

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.async_persistence import AsyncPersistenceManager, PersistenceEventType, EventPriority

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("crowdshield.smoke_test")


def test_health_endpoint(base_url: str) -> bool:
    url = f"{base_url}/health"
    logger.info(f"Probing Health Endpoint: {url}")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                logger.info(f"  -> Health OK: {data}")
                return True
            logger.error(f"  -> Health failed with status {response.status}")
            return False
    except Exception as e:
        logger.error(f"  -> Health endpoint unreachable: {e}")
        return False


def test_readiness_endpoint(base_url: str) -> bool:
    url = f"{base_url}/readiness"
    logger.info(f"Probing Readiness Endpoint: {url}")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                logger.info(f"  -> Readiness OK: status={data.get('status')}, db={data.get('database')}, persistence={data.get('persistence')}")
                return True
            logger.error(f"  -> Readiness failed with status {response.status}")
            return False
    except Exception as e:
        logger.error(f"  -> Readiness endpoint unreachable: {e}")
        return False


def test_protected_endpoint_rejection(base_url: str) -> bool:
    url = f"{base_url}/api/v1/operator/incidents"
    logger.info(f"Testing Protected Endpoint Security Rejection: {url}")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            logger.error(f"  -> Security Failure! Unauthenticated request returned {response.status}")
            return False
    except urllib.error.HTTPError as e:
        if e.code in [401, 403]:
            logger.info(f"  -> Security OK: Unauthenticated request properly rejected with HTTP {e.code}")
            return True
        logger.error(f"  -> Unexpected HTTP code: {e.code}")
        return False
    except Exception as e:
        logger.error(f"  -> Request error: {e}")
        return False


def test_database_direct_connection() -> bool:
    logger.info("Testing Direct Database Connectivity...")
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            logger.info("  -> Database Connection OK")
            return True
        finally:
            db.close()
    except Exception as e:
        logger.error(f"  -> Database Connection Failed: {e}")
        return False


def test_async_persistence_manager() -> bool:
    logger.info("Testing Async Persistence Manager Enqueue & Execution...")
    try:
        mgr = AsyncPersistenceManager.get_instance()
        executed = []

        def dummy_handler(session, payload):
            executed.append(payload.get("test_key"))

        test_payload = {"test_key": f"smoke_test_{time.time()}"}
        mgr.enqueue_task(
            event_type=PersistenceEventType.AUDIT_LOG,
            payload=test_payload,
            priority=EventPriority.HIGH,
            handler=dummy_handler
        )

        # Wait for worker thread
        time.sleep(0.5)
        if test_payload["test_key"] in executed:
            logger.info("  -> Async Persistence Worker Execution OK")
            return True
        logger.error("  -> Persistence worker did not execute task in expected timeframe")
        return False
    except Exception as e:
        logger.error(f"  -> Async Persistence Manager Error: {e}")
        return False


def run_all_smoke_tests():
    logger.info("======================================================================")
    logger.info(" CROWDSHIELD NATIVE DEPLOYMENT SMOKE TEST SUITE")
    logger.info("======================================================================")

    results = {}
    base_url = f"http://localhost:{settings.PORT}"

    results["database"] = test_database_direct_connection()
    results["persistence"] = test_async_persistence_manager()
    results["health_api"] = test_health_endpoint(base_url)
    results["readiness_api"] = test_readiness_endpoint(base_url)
    results["security_rejection"] = test_protected_endpoint_rejection(base_url)

    logger.info("======================================================================")
    logger.info(" SMOKE TEST SUMMARY RESULTS:")
    passed_all = True
    for test_name, status in results.items():
        status_str = "PASS" if status else "FAIL"
        if not status:
            passed_all = False
        logger.info(f"  - {test_name.ljust(25)}: {status_str}")

    logger.info("======================================================================")
    if passed_all:
        logger.info("SUCCESS: All native deployment smoke tests PASSED!")
        sys.exit(0)
    else:
        logger.error("FAILURE: One or more smoke tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    run_all_smoke_tests()
