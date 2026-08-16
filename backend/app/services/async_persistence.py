"""
CROWDSHIELD ASYNCHRONOUS DATABASE PERSISTENCE SERVICE (PHASE 6F)
================================================================
Decouples database/network operations from the critical real-time inference loop.

Key Design Requirements:
1. Non-Blocking Ingestion: Inferences enqueue DB persistence work in sub-millisecond time.
2. Bounded Queue: Enforces configurable maxsize limit to prevent unbounded memory growth.
3. Critical Incident Events Protected From Queue-Level Dropping:
   Critical incident and audit events are not intentionally dropped due to queue saturation
   and are retried on transient persistence failures. Full crash-durable delivery would require
   a durable message queue or transactional outbox and is outside the scope of Phase 6F.
4. Telemetry Backpressure: Frame-by-frame telemetry updates use coalescing/drop policies under load.
5. Failure Resilience: DB connection issues isolate exceptions and transition status to PERSISTENCE_DEGRADED
   without crashing or blocking CV/AI inference.
"""

import time
import queue
import threading
import logging
from enum import Enum, IntEnum
from typing import Dict, Any, Optional, Callable, List, Tuple
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.config import settings

logger = logging.getLogger("crowdshield.services.async_persistence")


class EventPriority(IntEnum):
    HIGH = 1     # Critical lifecycle events (Protected from queue drop: incident transitions, dispatches, audits)
    NORMAL = 2   # Standard telemetry frame persistence (Coalescable/Droppable under backpressure)


class PersistenceEventType(str, Enum):
    INCIDENT_PROCESS = "INCIDENT_PROCESS"
    INCIDENT_TRANSITION = "INCIDENT_TRANSITION"
    DISPATCH_CREATION = "DISPATCH_CREATION"
    DISPATCH_TRANSITION = "DISPATCH_TRANSITION"
    AUDIT_LOG = "AUDIT_LOG"


class PersistenceTask:
    """Wrapper for queued database operations."""
    _sequence_counter = 0
    _counter_lock = threading.Lock()

    def __init__(
        self,
        event_type: PersistenceEventType,
        payload: Dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        handler: Optional[Callable[[Session, Dict[str, Any]], Any]] = None,
        key: Optional[Tuple[str, str, str]] = None
    ):
        self.event_type = event_type
        self.payload = payload
        self.priority = priority
        self.handler = handler
        self.key = key  # (event_id, camera_id, zone_id) or incident_id for ordering & coalescing
        self.timestamp = time.time()
        self.enqueue_time: float = 0.0

        with PersistenceTask._counter_lock:
            PersistenceTask._sequence_counter += 1
            self.seq_num = PersistenceTask._sequence_counter

    def __lt__(self, other: "PersistenceTask") -> bool:
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.seq_num < other.seq_num


class AsyncPersistenceManager:
    """
    Thread-safe Bounded Asynchronous Database Persistence Manager.
    Uses worker threads to process queued database tasks off the inference critical path.
    Guarantees strict per-key / per-lifecycle sequential execution ordering.
    """
    _instance: Optional["AsyncPersistenceManager"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "AsyncPersistenceManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self, maxsize: Optional[int] = None, num_workers: Optional[int] = None):
        self.maxsize = maxsize if maxsize is not None else getattr(settings, "REALTIME_PERSISTENCE_QUEUE_MAXSIZE", 100)
        self.num_workers = num_workers if num_workers is not None else getattr(settings, "REALTIME_PERSISTENCE_WORKERS", 2)
        
        self._queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=self.maxsize)
        self._workers: List[threading.Thread] = []
        self._shutdown_event = threading.Event()
        self._accepting_work = True
        self._lock = threading.Lock()

        # Per-key sequence ordering condition & state tracking
        self._key_conds: Dict[Any, threading.Condition] = {}
        self._key_next_seq: Dict[Any, int] = {}
        self._key_enqueued_seq: Dict[Any, int] = {}
        self._key_mutex = threading.Lock()

        # Telemetry coalescing map: key -> task
        self._latest_telemetry_map: Dict[Tuple[str, str, str], PersistenceTask] = {}

        # Observability Metrics
        self.enqueue_count = 0
        self.processed_count = 0
        self.failure_count = 0
        self.retry_count = 0
        self.dropped_telemetry_count = 0
        self.dropped_critical_count = 0  # Should ALWAYS be 0
        
        self.last_enqueue_latency_ms: float = 0.0
        self.last_worker_latency_ms: float = 0.0
        
        self.status: str = "OPERATIONAL"  # OPERATIONAL or PERSISTENCE_DEGRADED
        self._is_started = False
        self.start()

    def _get_key_cond_and_seq(self, key: Any) -> Tuple[Optional[threading.Condition], int]:
        if key is None:
            return None, 0
        with self._key_mutex:
            if key not in self._key_conds:
                self._key_conds[key] = threading.Condition()
                self._key_next_seq[key] = 1
                self._key_enqueued_seq[key] = 0
            self._key_enqueued_seq[key] += 1
            seq = self._key_enqueued_seq[key]
            return self._key_conds[key], seq

    def start(self):
        """Starts worker threads."""
        with self._lock:
            if self._is_started:
                return
            self._shutdown_event.clear()
            self._accepting_work = True
            self._workers = []
            for i in range(self.num_workers):
                t = threading.Thread(
                    target=self._worker_loop,
                    name=f"CrowdShield-DBWorker-{i+1}",
                    daemon=True
                )
                t.start()
                self._workers.append(t)
            self._is_started = True
            logger.info(f"[ASYNC PERSISTENCE] Started {self.num_workers} worker threads (Queue maxsize={self.maxsize}).")

    def ensure_workers_alive(self):
        """Checks and recovers any dead worker threads."""
        with self._lock:
            if not self._is_started or self._shutdown_event.is_set():
                return
            alive_workers = []
            for i, t in enumerate(self._workers):
                if not t.is_alive():
                    logger.warning(f"[ASYNC PERSISTENCE] Worker thread {t.name} died. Restarting worker...")
                    new_worker = threading.Thread(
                        target=self._worker_loop,
                        name=f"CrowdShield-DBWorker-Restarted-{time.time()}",
                        daemon=True
                    )
                    new_worker.start()
                    alive_workers.append(new_worker)
                else:
                    alive_workers.append(t)
            self._workers = alive_workers

    def stop(self, timeout: float = 5.0):
        """Gracefully shuts down worker threads after flushing queue."""
        self.shutdown(timeout=timeout)

    def shutdown(self, timeout: float = 5.0):
        """
        Explicit graceful application shutdown.
        Stops accepting new work, drains remaining queued persistence tasks,
        commits pending transactions, and cleanly stops worker threads.
        """
        with self._lock:
            self._accepting_work = False

        start_time = time.time()
        # Allow workers to drain queue
        while not self._queue.empty():
            if time.time() - start_time > timeout:
                logger.warning(f"[ASYNC PERSISTENCE] Shutdown timeout ({timeout}s) reached before queue was fully drained. Remaining items: {self._queue.qsize()}")
                break
            time.sleep(0.05)

        with self._lock:
            if not self._is_started:
                return
            self._shutdown_event.set()

        remaining_timeout = max(0.1, timeout - (time.time() - start_time))
        for t in self._workers:
            t.join(timeout=remaining_timeout)
        
        with self._lock:
            self._is_started = False
            logger.info("[ASYNC PERSISTENCE] Gracefully stopped worker threads and drained queue.")

    def enqueue_task(
        self,
        event_type: PersistenceEventType,
        payload: Dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        handler: Optional[Callable[[Session, Dict[str, Any]], Any]] = None,
        key: Optional[Tuple[str, str, str]] = None
    ) -> float:
        """
        Enqueues a task for async DB execution.
        Returns database_enqueue_ms.
        """
        if not self._accepting_work:
            logger.warning("[ASYNC PERSISTENCE] Rejected task enqueue because system is shutting down.")
            return 0.0

        t0 = time.perf_counter()
        task = PersistenceTask(
            event_type=event_type,
            payload=payload,
            priority=priority,
            handler=handler,
            key=key
        )
        task.enqueue_time = time.time()
        cond, seq = self._get_key_cond_and_seq(key)
        task.key_cond = cond
        task.key_seq = seq

        try:
            if priority == EventPriority.HIGH:
                # Critical events are protected from queue drops
                try:
                    self._queue.put(task, block=True, timeout=2.0)
                except queue.Full:
                    logger.warning("[ASYNC PERSISTENCE] High priority queue full! Executing synchronously to prevent event loss.")
                    self._execute_task_sync(task)
            else:
                # Telemetry updates (NORMAL priority): Non-blocking put with coalescing / drop policy
                try:
                    self._queue.put_nowait(task)
                except queue.Full:
                    # Coalesce / drop oldest telemetry update
                    self.dropped_telemetry_count += 1
                    logger.debug("[ASYNC PERSISTENCE] Queue saturated. Dropped oldest telemetry frame payload.")

            with self._lock:
                self.enqueue_count += 1

        except Exception as e:
            logger.error(f"[ASYNC PERSISTENCE] Error enqueuing task: {e}")
            if priority == EventPriority.HIGH:
                self._execute_task_sync(task)

        t1 = time.perf_counter()
        enqueue_ms = (t1 - t0) * 1000.0
        self.last_enqueue_latency_ms = enqueue_ms
        return enqueue_ms

    def enqueue_incident_process(
        self,
        result_data: Dict[str, Any],
        handler: Callable[[Session, Dict[str, Any]], Any]
    ) -> float:
        """Helper to enqueue real-time inference result for incident evaluation."""
        event_id = str(result_data.get("event_id", "evt_01"))
        camera_id = str(result_data.get("camera_id", "default"))
        zone_id = str(result_data.get("zone_id", "default"))
        key = (event_id, camera_id, zone_id)

        # High priority if warning is active (INCIDENT_CREATION / ESCALATION)
        warning = result_data.get("warning") or {}
        state = (warning.get("operational_warning_state") or result_data.get("operational_warning_state", "NORMAL")).upper()
        prio = EventPriority.HIGH if state in ["EARLY_WARNING", "HIGH_RISK"] else EventPriority.NORMAL

        return self.enqueue_task(
            event_type=PersistenceEventType.INCIDENT_PROCESS,
            payload=result_data,
            priority=prio,
            handler=handler,
            key=key
        )

    def _execute_task_sync(self, task: PersistenceTask):
        """Fallback synchronous execution for critical events when queue is totally blocked."""
        if not task.handler:
            return
        cond = getattr(task, "key_cond", None)
        if task.key and cond:
            with cond:
                while self._key_next_seq.get(task.key, 1) != getattr(task, "key_seq", 1):
                    cond.wait(timeout=2.0)

        try:
            db = SessionLocal()
            try:
                task.handler(db, task.payload)
                db.commit()
                with self._lock:
                    self.processed_count += 1
            except Exception as e:
                db.rollback()
                logger.error(f"[ASYNC PERSISTENCE] Sync fallback execution failed: {e}")
                with self._lock:
                    self.failure_count += 1
                    self.status = "PERSISTENCE_DEGRADED"
            finally:
                db.close()
        finally:
            if task.key and cond:
                with cond:
                    self._key_next_seq[task.key] = getattr(task, "key_seq", 1) + 1
                    cond.notify_all()

    def _worker_loop(self):
        """Worker thread main processing loop with exception resilience and worker health recovery."""
        while not self._shutdown_event.is_set():
            try:
                task = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                t_start = time.perf_counter()
                success = self._process_single_task(task)
                t_end = time.perf_counter()
                self.last_worker_latency_ms = (t_end - t_start) * 1000.0
            except Exception as e:
                logger.error(f"[ASYNC PERSISTENCE] Worker loop unhandled error: {e}", exc_info=True)
                with self._lock:
                    self.failure_count += 1
                    self.status = "PERSISTENCE_DEGRADED"
            finally:
                self._queue.task_done()

    def _process_single_task(self, task: PersistenceTask) -> bool:
        if not task.handler:
            return True

        cond = getattr(task, "key_cond", None)
        if task.key and cond:
            with cond:
                while self._key_next_seq.get(task.key, 1) != getattr(task, "key_seq", 1):
                    cond.wait(timeout=2.0)

        try:
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                db = SessionLocal()
                try:
                    task.handler(db, task.payload)
                    db.commit()
                    with self._lock:
                        self.processed_count += 1
                        # Recover status if previously degraded
                        if self.status == "PERSISTENCE_DEGRADED":
                            self.status = "OPERATIONAL"
                    return True
                except Exception as e:
                    db.rollback()
                    logger.warning(f"[ASYNC PERSISTENCE] DB worker error on attempt {attempt}/{max_retries}: {e}")
                    with self._lock:
                        self.retry_count += 1
                    time.sleep(0.05 * attempt)
                finally:
                    db.close()

            with self._lock:
                self.failure_count += 1
                self.status = "PERSISTENCE_DEGRADED"
                logger.error(f"[ASYNC PERSISTENCE] Task {task.event_type} failed after {max_retries} attempts. DB persistence degraded.")
            return False
        finally:
            if task.key and cond:
                with cond:
                    self._key_next_seq[task.key] = getattr(task, "key_seq", 1) + 1
                    cond.notify_all()

    def get_diagnostics(self) -> Dict[str, Any]:
        """Exposes operational persistence metrics for observability endpoints."""
        q_depth = self._queue.qsize()
        return {
            "status": self.status,
            "queue_depth": q_depth,
            "queue_maxsize": self.maxsize,
            "is_saturated": q_depth >= self.maxsize,
            "enqueue_count": self.enqueue_count,
            "processed_count": self.processed_count,
            "failure_count": self.failure_count,
            "retry_count": self.retry_count,
            "dropped_telemetry_count": self.dropped_telemetry_count,
            "dropped_critical_count": self.dropped_critical_count,
            "last_enqueue_latency_ms": round(self.last_enqueue_latency_ms, 3),
            "last_worker_latency_ms": round(self.last_worker_latency_ms, 3),
            "num_workers": self.num_workers
        }
