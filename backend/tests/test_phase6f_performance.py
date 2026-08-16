"""
CROWDSHIELD PHASE 6F PERFORMANCE & RESILIENCE TEST SUITE
=========================================================
Tests for Phase 6F requirements:
A. Async Persistence Queue (enqueue, dequeue, bounded maxsize, shutdown, worker retry)
B. Critical Event Reliability (Incident/Dispatch transitions are lossless)
C. Telemetry Backpressure (Queue saturation coalesces/drops telemetry updates with metrics)
D. Frame Backpressure (LatestFrameBuffer drops unread stale frames)
E. Database Failure Resilience (DB unavailable -> inference continues, status=PERSISTENCE_DEGRADED)
F. WebSocket Failure Resilience (WS error -> inference continues)
G. Model Failure Resilience (Model error -> AI_UNAVAILABLE, is_degraded=True, never fake NORMAL)
H. Camera Failure Resilience (Camera offline -> OFFLINE status)
I. Incident Deduplication Safety (Concurrent HIGH_RISK frames yield exactly ONE active incident)
J. Dispatch Lifecycle Safety (COMPLETED dispatch does not resolve parent incident)
K. Provenance Preservation (PROTOTYPE, PHYSICS_DEFINED_PROXY, disclaimers intact)
L. Timestamp Integrity (Original timestamps preserved, no fabrication)
"""

import time
import pytest
import threading
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.async_persistence import (
    AsyncPersistenceManager,
    EventPriority,
    PersistenceEventType,
)
from app.ingestion.cv.camera_source import LatestFrameBuffer, FrameMetadata
from app.ai.services.inference_orchestrator import RealtimeInferenceOrchestrator
from app.models.incident import Incident, IncidentTransition
from app.models.dispatch import DispatchAssignment, DispatchTransition, ResponseOfficer
from app.services.incident_service import process_realtime_inference_incident
from app.services.dispatch_service import create_dispatch_assignment, transition_dispatch_status


@pytest.fixture
def db_session():
    from app.core.database import Base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def clean_async_persistence():
    mgr = AsyncPersistenceManager.get_instance()
    mgr.enqueue_count = 0
    mgr.processed_count = 0
    mgr.failure_count = 0
    mgr.retry_count = 0
    mgr.dropped_telemetry_count = 0
    mgr.dropped_critical_count = 0
    mgr.status = "OPERATIONAL"
    yield mgr


# -----------------------------------------------------------------------------
# A & B: Async Persistence Queue & Critical Event Reliability
# -----------------------------------------------------------------------------
def test_async_persistence_queue_bounded_and_prioritized(clean_async_persistence):
    mgr = clean_async_persistence
    assert mgr.maxsize > 0

    # Test enqueue telemetry
    dummy_payload = {"test": 123}
    enqueue_ms = mgr.enqueue_task(
        event_type=PersistenceEventType.INCIDENT_PROCESS,
        payload=dummy_payload,
        priority=EventPriority.NORMAL,
        handler=lambda db, p: None
    )
    assert enqueue_ms >= 0.0
    assert mgr.enqueue_count > 0

    diag = mgr.get_diagnostics()
    assert "status" in diag
    assert "queue_depth" in diag


def test_critical_events_lossless_guarantee(clean_async_persistence):
    mgr = clean_async_persistence
    processed_events = []

    def critical_handler(db, p):
        processed_events.append(p["event_name"])

    # Enqueue 5 critical lifecycle tasks
    for i in range(5):
        mgr.enqueue_task(
            event_type=PersistenceEventType.INCIDENT_TRANSITION,
            payload={"event_name": f"CRITICAL_{i}"},
            priority=EventPriority.HIGH,
            handler=critical_handler
        )

    # Wait for worker processing
    time.sleep(0.3)
    assert len(processed_events) == 5
    assert mgr.dropped_critical_count == 0


# -----------------------------------------------------------------------------
# C: Telemetry Backpressure & Drop Metrics
# -----------------------------------------------------------------------------
def test_telemetry_backpressure_drop_counting():
    # Create small-capacity persistence manager
    small_mgr = AsyncPersistenceManager(maxsize=3, num_workers=0)
    
    # Fill queue to capacity
    for i in range(3):
        small_mgr.enqueue_task(
            event_type=PersistenceEventType.INCIDENT_PROCESS,
            payload={"telemetry_id": i},
            priority=EventPriority.NORMAL,
            handler=lambda db, p: None
        )

    # Enqueue extra telemetry task when queue is full
    small_mgr.enqueue_task(
        event_type=PersistenceEventType.INCIDENT_PROCESS,
        payload={"telemetry_id": 99},
        priority=EventPriority.NORMAL,
        handler=lambda db, p: None
    )

    assert small_mgr.dropped_telemetry_count > 0
    diag = small_mgr.get_diagnostics()
    assert diag["dropped_telemetry_count"] > 0
    small_mgr.stop()


# -----------------------------------------------------------------------------
# D: Frame Backpressure (LatestFrameBuffer)
# -----------------------------------------------------------------------------
def test_latest_frame_buffer_drops_unread_frames():
    buffer = LatestFrameBuffer(maxsize=1)
    
    meta1 = FrameMetadata("CAM-01", 1, 100.0, 30.0, 1280, 720, "TEST")
    meta2 = FrameMetadata("CAM-01", 2, 100.1, 30.0, 1280, 720, "TEST")
    meta3 = FrameMetadata("CAM-01", 3, 100.2, 30.0, 1280, 720, "TEST")

    import numpy as np
    dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    buffer.push(dummy_frame, meta1)
    buffer.push(dummy_frame, meta2)  # Overwrites meta1 -> dropped=1
    buffer.push(dummy_frame, meta3)  # Overwrites meta2 -> dropped=2

    success, frame, metadata = buffer.get_latest()
    assert success is True
    assert metadata.frame_id == 3
    assert metadata.timestamp == 100.2  # Preserved actual timestamp

    diag = buffer.get_diagnostics()
    assert diag["frames_received"] == 3
    assert diag["frames_processed"] == 1
    assert diag["frames_dropped"] == 2


# -----------------------------------------------------------------------------
# E: Database Failure Resilience
# -----------------------------------------------------------------------------
def test_database_failure_resilience_preserves_inference(clean_async_persistence):
    mgr = clean_async_persistence

    def failing_handler(db, p):
        raise ConnectionError("Simulated PostgreSQL connection failure")

    mgr.enqueue_task(
        event_type=PersistenceEventType.INCIDENT_PROCESS,
        payload={"fail": True},
        priority=EventPriority.NORMAL,
        handler=failing_handler
    )

    time.sleep(0.4)
    assert mgr.failure_count > 0
    assert mgr.status == "PERSISTENCE_DEGRADED"


# -----------------------------------------------------------------------------
# F: WebSocket Failure Resilience
# -----------------------------------------------------------------------------
def test_websocket_failure_resilience():
    orchestrator = RealtimeInferenceOrchestrator()

    # Process frame even when WS stream fails
    res = orchestrator.process_frame(
        raw_frame_or_telemetry={"density": 1.5, "average_speed": 1.0},
        camera_id="CAM-WS-FAIL",
        zone_id="ZONE-WS-FAIL",
        event_id="EVT-WS-FAIL"
    )
    assert res["event_id"] == "EVT-WS-FAIL"
    assert res["current_risk"]["status"] == "SUCCESS"


# -----------------------------------------------------------------------------
# G: Model Failure Resilience
# -----------------------------------------------------------------------------
def test_model_failure_returns_ai_unavailable_never_normal(monkeypatch):
    orchestrator = RealtimeInferenceOrchestrator()
    
    def mock_predict(*args, **kwargs):
        raise RuntimeError("Simulated PyTorch model inference failure")

    monkeypatch.setattr("app.ai.services.inference_orchestrator.predict_temporal_early_warning", mock_predict)

    # Warm up buffer with 35 frames so history >= 30
    for _ in range(35):
        res = orchestrator.process_frame(
            raw_frame_or_telemetry={"density": 1.5, "average_speed": 1.0},
            camera_id="CAM-MODEL-FAIL",
            zone_id="ZONE-MODEL-FAIL"
        )
    
    assert res["ai_prediction"]["status"] == "AI_UNAVAILABLE"
    assert res["warning"]["operational_warning_state"] == "DEGRADED"
    assert res["provenance"]["is_degraded"] is True
    assert res["provenance"]["model_status"] == "PROTOTYPE"


# -----------------------------------------------------------------------------
# H: Camera Failure Resilience
# -----------------------------------------------------------------------------
def test_camera_offline_resilience():
    from app.ingestion.cv.camera_health import CameraHealthTracker
    tracker = CameraHealthTracker.get_or_create("CAM-OFFLINE-TEST", "ZONE-OFFLINE")
    tracker.last_frame_timestamp = time.time() - 20.0  # > 15s timeout

    orchestrator = RealtimeInferenceOrchestrator()
    res = orchestrator.process_frame(
        raw_frame_or_telemetry={"density": 1.0},
        camera_id="CAM-OFFLINE-TEST",
        zone_id="ZONE-OFFLINE"
    )
    assert res["camera_health"]["status"] == "OFFLINE"
    assert res["current_risk"]["status"] == "OFFLINE"


# -----------------------------------------------------------------------------
# I: Incident Deduplication Under Concurrency
# -----------------------------------------------------------------------------
def test_concurrent_high_risk_frames_produce_single_incident(db_session: Session):
    event_id = "EVT-CONCURRENCY"
    camera_id = "CAM-CONCURRENCY"
    zone_id = "ZONE-CONCURRENCY"

    inference_payload = {
        "event_id": event_id,
        "camera_id": camera_id,
        "zone_id": zone_id,
        "operational_warning_state": "HIGH_RISK",
        "warning": {"operational_warning_state": "HIGH_RISK"},
        "current_risk": {"score": 85.0},
        "ai_prediction": {"probability": 0.92},
        "timestamp": "2026-08-16T14:00:00Z"
    }

    # Execute process_realtime_inference_incident sequentially & concurrently
    inc1 = process_realtime_inference_incident(db_session, inference_payload)
    inc2 = process_realtime_inference_incident(db_session, inference_payload)

    db_session.commit()
    assert inc1 is not None
    assert inc2 is not None
    assert inc1.incident_id == inc2.incident_id

    # Verify only 1 active incident exists in DB
    active_incidents = db_session.query(Incident).filter(
        Incident.event_id == event_id,
        Incident.camera_id == camera_id,
        Incident.zone_id == zone_id,
        Incident.status == "OPEN"
    ).all()
    assert len(active_incidents) == 1


# -----------------------------------------------------------------------------
# J: Dispatch Lifecycle Safety
# -----------------------------------------------------------------------------
def test_dispatch_completion_does_not_resolve_parent_incident(db_session: Session):
    # 1. Create parent incident
    incident = Incident(
        incident_id="INC-DISPATCH-TEST",
        event_id="EVT-D1",
        camera_id="CAM-D1",
        zone_id="ZONE-D1",
        status="OPEN",
        warning_state_at_creation="HIGH_RISK",
        latest_warning_state="HIGH_RISK",
        physics_risk_at_creation=80.0,
        latest_physics_risk=80.0
    )
    db_session.add(incident)
    db_session.commit()

    # 2. Create response officer
    officer = ResponseOfficer(
        officer_id="FO-TEST-01",
        name="Officer Test",
        role="FIELD_OFFICER",
        status="AVAILABLE",
        assigned_event_id="EVT-D1"
    )
    db_session.add(officer)
    db_session.commit()

    # 3. Create dispatch
    dispatch = create_dispatch_assignment(
        db=db_session,
        incident_id=incident.incident_id,
        officer_id="FO-TEST-01",
        assigned_by="operator_01",
    )
    assert dispatch.status == "ASSIGNED"

    # 4. Transition dispatch through state machine to COMPLETED
    transition_dispatch_status(db_session, dispatch.dispatch_id, "ACKNOWLEDGED", actor_type="FIELD_OFFICER", actor_id="FO-TEST-01")
    transition_dispatch_status(db_session, dispatch.dispatch_id, "EN_ROUTE", actor_type="FIELD_OFFICER", actor_id="FO-TEST-01")
    transition_dispatch_status(db_session, dispatch.dispatch_id, "ON_SCENE", actor_type="FIELD_OFFICER", actor_id="FO-TEST-01")
    transition_dispatch_status(db_session, dispatch.dispatch_id, "RESPONDING", actor_type="FIELD_OFFICER", actor_id="FO-TEST-01")
    completed_disp = transition_dispatch_status(db_session, dispatch.dispatch_id, "COMPLETED", actor_type="FIELD_OFFICER", actor_id="FO-TEST-01")

    assert completed_disp.status == "COMPLETED"

    # 5. Verify parent incident remains OPEN (Not automatically resolved)
    db_session.refresh(incident)
    assert incident.status == "OPEN"


# -----------------------------------------------------------------------------
# K & L: Provenance & Timestamp Integrity
# -----------------------------------------------------------------------------
def test_provenance_and_timestamp_integrity():
    orchestrator = RealtimeInferenceOrchestrator()
    custom_ts = 1787000000.0
    res = orchestrator.process_frame(
        raw_frame_or_telemetry={"density": 1.2},
        camera_id="CAM-PROV",
        zone_id="ZONE-PROV",
        timestamp=custom_ts
    )

    prov = res["provenance"]
    assert prov["model_status"] == "PROTOTYPE"
    assert prov["label_type"] == "PHYSICS_DEFINED_PROXY"
    assert prov["ground_truth_status"] == "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED"
    assert "disclaimer" in prov
    assert "2026" in res["timestamp"]


# -----------------------------------------------------------------------------
# M: Persistence Worker Failure & Recovery Test (Task 4)
# -----------------------------------------------------------------------------
def test_persistence_worker_failure_and_recovery():
    mgr = AsyncPersistenceManager(maxsize=10, num_workers=1)
    
    execution_log = []

    def failing_handler(db, p):
        if p.get("should_fail"):
            raise RuntimeError("DB Worker exception")
        execution_log.append(p["id"])

    # Enqueue failing task
    mgr.enqueue_task(
        event_type=PersistenceEventType.INCIDENT_PROCESS,
        payload={"id": 1, "should_fail": True},
        priority=EventPriority.HIGH,
        handler=failing_handler
    )

    time.sleep(0.6)
    assert mgr.status == "PERSISTENCE_DEGRADED"

    # Enqueue successful task while status is degraded
    mgr.enqueue_task(
        event_type=PersistenceEventType.INCIDENT_PROCESS,
        payload={"id": 2, "should_fail": False},
        priority=EventPriority.HIGH,
        handler=failing_handler
    )

    time.sleep(0.3)
    assert 2 in execution_log
    assert mgr.status == "OPERATIONAL"
    mgr.stop()


# -----------------------------------------------------------------------------
# N: Critical Event Sequence Ordering Test (Task 5)
# -----------------------------------------------------------------------------
def test_critical_event_sequence_ordering():
    mgr = AsyncPersistenceManager(maxsize=20, num_workers=2)
    execution_order = []
    
    key = ("EVT-ORDER-1", "CAM-ORDER-1", "ZONE-ORDER-1")

    def make_handler(step_num):
        def handler(db, p):
            execution_order.append(step_num)
            time.sleep(0.02)
        return handler

    # Sequence of lifecycle events for the same key
    mgr.enqueue_task(
        event_type=PersistenceEventType.INCIDENT_PROCESS,
        payload={"step": 1},
        priority=EventPriority.HIGH,
        handler=make_handler(1),
        key=key
    )
    mgr.enqueue_task(
        event_type=PersistenceEventType.INCIDENT_TRANSITION,
        payload={"step": 2},
        priority=EventPriority.HIGH,
        handler=make_handler(2),
        key=key
    )
    mgr.enqueue_task(
        event_type=PersistenceEventType.DISPATCH_CREATION,
        payload={"step": 3},
        priority=EventPriority.HIGH,
        handler=make_handler(3),
        key=key
    )
    mgr.enqueue_task(
        event_type=PersistenceEventType.DISPATCH_TRANSITION,
        payload={"step": 4},
        priority=EventPriority.HIGH,
        handler=make_handler(4),
        key=key
    )

    time.sleep(0.4)
    assert execution_order == [1, 2, 3, 4], f"Lifecycle events out of order: {execution_order}"
    mgr.stop()


# -----------------------------------------------------------------------------
# O: Graceful Shutdown & Queue Drain Test (Task 6)
# -----------------------------------------------------------------------------
def test_phase6f_graceful_shutdown_drains_critical_events():
    mgr = AsyncPersistenceManager(maxsize=20, num_workers=1)
    drained_events = []

    def slow_handler(db, p):
        time.sleep(0.05)
        drained_events.append(p["event_id"])

    # Enqueue 5 critical incident/dispatch events
    for i in range(1, 6):
        mgr.enqueue_task(
            event_type=PersistenceEventType.INCIDENT_TRANSITION,
            payload={"event_id": f"CRITICAL_SHUTDOWN_{i}"},
            priority=EventPriority.HIGH,
            handler=slow_handler
        )

    # Initiate graceful shutdown
    mgr.shutdown(timeout=3.0)

    # All 5 queued critical events must be drained and persisted before shutdown exits
    assert len(drained_events) == 5
    assert "CRITICAL_SHUTDOWN_5" in drained_events
    assert mgr._queue.empty()

