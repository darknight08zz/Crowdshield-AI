"""
CROWDSHIELD LOAD & CONCURRENCY STRESS TEST
==========================================
Simulates real event concurrency: dozens of zones querying risk API, mass incident reporting bursts,
and recommendation evaluation under parallel load pressure.
"""

import time
import concurrent.futures
import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.core.config import settings

TARGET_ZONE_ID = "aa111111-0000-0000-0000-000000000001"


def get_auth_headers():
    token = jwt.encode({"sub": "00000000-0000-0000-0000-000000000001", "role": "operator"}, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def make_risk_query(zone_id: str):
    client = TestClient(app)
    headers = get_auth_headers()
    start = time.time()
    res = client.get(f"/api/v1/operator/zones/{zone_id}/risk", headers=headers)
    duration_ms = (time.time() - start) * 1000.0
    return res.status_code, duration_ms


def make_incident_report(zone_id: str, index: int):
    client = TestClient(app)
    headers = get_auth_headers()
    start = time.time()
    payload = {
        "zone_id": zone_id,
        "title": f"Load Test Incident Burst #{index}",
        "description": "Mass report spike test",
        "category": "overcrowding"
    }
    res = client.post("/api/v1/citizens/incidents", json=payload, headers=headers)
    duration_ms = (time.time() - start) * 1000.0
    return res.status_code, duration_ms


def test_concurrent_risk_evaluations_load():
    """Simulates 30 concurrent operator dashboard risk evaluations."""
    num_requests = 30
    durations = []
    handled_count = 0
    server_error_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_risk_query, TARGET_ZONE_ID) for _ in range(num_requests)]
        for f in concurrent.futures.as_completed(futures):
            status, dur = f.result()
            if status < 500:  # Any handled response (200, 404, 429) without 500 crash
                handled_count += 1
            if status >= 500:
                server_error_count += 1
            durations.append(dur)

    durations.sort()
    p50 = durations[int(len(durations) * 0.50)]
    p95 = durations[int(len(durations) * 0.95)]

    print(f"\n[+] LOAD TEST - {num_requests} CONCURRENT RISK EVALUATIONS:")
    print(f"    - Handled Gracefully: {handled_count}/{num_requests} ({(handled_count/num_requests)*100:.1f}%)")
    print(f"    - Server 500 Errors:  {server_error_count}")
    print(f"    - Latency p50:        {p50:.1f} ms")
    print(f"    - Latency p95:        {p95:.1f} ms")

    assert handled_count == num_requests
    assert server_error_count == 0


def test_mass_incident_reporting_burst():
    """Simulates a sudden burst of 15 simultaneous citizen incident reports (verifies zero server crashes)."""
    num_reports = 15
    handled_count = 0
    server_error_count = 0
    durations = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_incident_report, TARGET_ZONE_ID, i) for i in range(num_reports)]
        for f in concurrent.futures.as_completed(futures):
            status, dur = f.result()
            if status < 500:  # Handled status code without unhandled 500 crash
                handled_count += 1
            if status >= 500:
                server_error_count += 1
            durations.append(dur)

    print(f"\n[+] BURST TEST - {num_reports} SIMULTANEOUS INCIDENT REPORTS:")
    print(f"    - Handled Gracefully: {handled_count}/{num_reports} ({(handled_count/num_reports)*100:.1f}%)")
    print(f"    - Server 500 Errors:  {server_error_count}")

    assert handled_count == num_reports
    assert server_error_count == 0
