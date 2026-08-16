"""
CROWDSHIELD REALTIME WEBSOCKET STREAM MANAGER (PHASE 6B)
========================================================
Asynchronous WebSocket connection registry and pub-sub manager for broadcasting
RealtimeInferenceResult updates to authenticated, subscribed clients.

Design principles:
- Every background task (sender, heartbeat) has a deterministic lifecycle.
- Disconnect cancels all tasks and awaits their completion before removing the session.
- Bounded queues (maxsize configurable) prevent slow clients from blocking the pipeline.
- A sentinel value (_STOP_SENTINEL) terminates the sender loop cleanly without polling.
- No asyncio.sleep-based polling in the sender or heartbeat loops.
- JWT authentication reuses app.core.security without duplication.
- Subscription isolation enforces (event_id, camera_id, zone_id) independence.

Backpressure policy:
  If the per-client queue is full, the oldest un-delivered item is dropped
  and the newest result is enqueued. The operator always receives the current state.

Structured log events emitted:
  CLIENT_CONNECTED, CLIENT_AUTHENTICATED, SUBSCRIPTION_CREATED,
  SUBSCRIPTION_REMOVED, INFERENCE_UPDATE_PUBLISHED, BACKPRESSURE_DROP,
  CLIENT_DISCONNECTED
"""

import asyncio
import logging
import uuid
from typing import Dict, Set, Any, Optional, Tuple

from fastapi import WebSocket, status

from app.core.security import decode_supabase_jwt, UserPayload
from app.schemas.realtime_inference import RealtimeInferenceResponse

logger = logging.getLogger("crowdshield.realtime.stream")

# Sentinel object — placed in the queue to signal the sender loop to stop.
_STOP_SENTINEL = object()


class ConnectionSession:
    """
    Represents a single authenticated WebSocket client connection.

    Lifecycle:
      __init__  → start_sender_loop()
                → (optionally) start_heartbeat_loop()
                → enqueue_payload() calls
                → stop() + await cleanup()
    """

    def __init__(
        self,
        websocket: Optional[WebSocket],
        client_id: str,
        user: Optional[UserPayload],
        queue_maxsize: int = 10,
    ):
        self.websocket = websocket
        self.client_id = client_id
        self.user = user
        self.subscriptions: Set[Tuple[str, str, str]] = set()  # (event_id, camera_id, zone_id)
        self.subscribe_all: bool = False
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=queue_maxsize)
        self.is_active: bool = True
        self._send_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Sender loop (runs as background asyncio.Task)
    # ------------------------------------------------------------------

    def start_sender_loop(self):
        """Starts the background sender task that drains the bounded queue."""
        self._send_task = asyncio.create_task(
            self._sender_loop(), name=f"sender-{self.client_id}"
        )

    async def _sender_loop(self):
        """
        Drains payloads from the bounded queue and sends them over WebSocket.
        Terminates when:
          - _STOP_SENTINEL is dequeued, OR
          - send fails (marks session inactive), OR
          - task is cancelled.
        """
        while True:
            try:
                payload = await self.queue.get()
            except asyncio.CancelledError:
                break

            if payload is _STOP_SENTINEL:
                self.queue.task_done()
                break

            try:
                if self.websocket is not None:
                    await self.websocket.send_json(payload)
            except Exception as exc:
                logger.warning(
                    "[WS STREAM] Send error for client %s: %s",
                    self.client_id,
                    exc,
                )
                self.is_active = False
                self.queue.task_done()
                break
            finally:
                # task_done only if we didn't break before it
                try:
                    self.queue.task_done()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Heartbeat loop (optional — started separately)
    # ------------------------------------------------------------------

    def start_heartbeat_loop(self, interval_seconds: float = 30.0):
        """Starts an optional heartbeat task that sends periodic pings."""
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(interval_seconds),
            name=f"heartbeat-{self.client_id}",
        )

    async def _heartbeat_loop(self, interval_seconds: float):
        """Sends a heartbeat ping every `interval_seconds` seconds."""
        try:
            while self.is_active:
                await asyncio.sleep(interval_seconds)
                if not self.is_active:
                    break
                self.enqueue_payload({"type": "ping", "source": "server"})
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Backpressure-aware enqueue
    # ------------------------------------------------------------------

    def enqueue_payload(self, payload: Dict[str, Any]) -> bool:
        """
        Enqueues payload with backpressure protection (non-blocking, thread-safe).

        If the queue is full, the oldest un-delivered item is discarded so the
        client receives the most current state.  The drop is logged.

        Returns True if enqueued, False if session is inactive.
        """
        if not self.is_active:
            return False

        try:
            self.queue.put_nowait(payload)
            return True
        except asyncio.QueueFull:
            # Drop oldest, insert newest
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except Exception:
                pass
            try:
                self.queue.put_nowait(payload)
                logger.debug(
                    "[WS STREAM] BACKPRESSURE_DROP: dropped stale item for slow client %s",
                    self.client_id,
                )
                return True
            except Exception:
                return False

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def stop(self):
        """
        Signals the sender loop to stop by:
          1. Setting is_active = False (prevents new enqueues).
          2. Enqueuing the sentinel (wakes the waiting sender loop).
          3. Cancelling the heartbeat task if running.
        """
        self.is_active = False

        # Wake up the sender loop via sentinel
        try:
            self.queue.put_nowait(_STOP_SENTINEL)
        except asyncio.QueueFull:
            # Drop oldest to make room for sentinel
            try:
                self.queue.get_nowait()
                self.queue.task_done()
                self.queue.put_nowait(_STOP_SENTINEL)
            except Exception:
                pass
        except Exception:
            pass

        # Cancel heartbeat
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()

        # Cancel sender as a fallback (sentinel should have already stopped it)
        if self._send_task and not self._send_task.done():
            self._send_task.cancel()

    async def wait_for_cleanup(self):
        """Awaits complete termination of all background tasks."""
        tasks = []
        if self._send_task and not self._send_task.done():
            tasks.append(self._send_task)
        if self._heartbeat_task and not self._heartbeat_task.done():
            tasks.append(self._heartbeat_task)

        for task in tasks:
            try:
                await asyncio.wait_for(task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception:
                pass


# ======================================================================
# RealtimeStreamManager
# ======================================================================


class RealtimeStreamManager:
    """
    Centralized real-time WebSocket connection registry and pub-sub broker.

    Responsibilities:
    - Authenticates incoming WebSocket connections (JWT via decode_supabase_jwt).
    - Manages per-connection session lifecycle.
    - Routes INFERENCE_UPDATE broadcasts to matching subscribers.
    - Enforces (event_id, camera_id, zone_id) subscription isolation.
    - Provides get_connection_stats() for the health endpoint.
    - Provides clear_all() for test tearDown.
    """

    def __init__(self):
        self._active_connections: Dict[str, ConnectionSession] = {}
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        """Returns an asyncio.Lock bound to the running event loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if self._lock is None or (
            loop is not None and getattr(self._lock, "_loop", None) is not loop
        ):
            self._lock = asyncio.Lock()
        return self._lock

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(
        self, websocket: WebSocket, token: Optional[str] = None
    ) -> Optional[ConnectionSession]:
        """
        Validates JWT, accepts the WebSocket handshake, creates and registers
        a new ConnectionSession, and starts its sender loop.

        Returns the session on success, or None if authentication fails
        (in which case the WebSocket is closed with WS_1008_POLICY_VIOLATION).
        """
        if not token:
            logger.warning("[WS STREAM] Rejected: missing token")
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Missing authentication token.",
            )
            return None

        try:
            jwt_payload = decode_supabase_jwt(token)
            user_id = str(jwt_payload.get("sub") or jwt_payload.get("id", "anon"))
            user_role = str(jwt_payload.get("role", "operator")).lower()
            user = UserPayload(
                id=user_id,
                email=jwt_payload.get("email"),
                role=user_role,
                account_status="active",
            )
        except Exception as exc:
            logger.warning("[WS STREAM] Rejected: invalid JWT (%s)", exc)
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid authentication token.",
            )
            return None

        await websocket.accept()

        client_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
        session = ConnectionSession(websocket, client_id, user)
        session.start_sender_loop()

        async with self._get_lock():
            self._active_connections[client_id] = session

        logger.info(
            "[WS STREAM] CLIENT_CONNECTED: %s (role=%s)", client_id, user.role
        )
        logger.info("[WS STREAM] CLIENT_AUTHENTICATED: %s", client_id)
        return session

    async def disconnect(self, client_id: str):
        """
        Removes the client from the registry, stops its background tasks,
        and awaits their complete termination.

        Lifecycle guarantee: after this coroutine returns, the client has
        zero registered resources (no tasks, no queue, no subscription).
        """
        async with self._get_lock():
            session = self._active_connections.pop(client_id, None)

        if session is None:
            return

        session.stop()
        await session.wait_for_cleanup()

        logger.info("[WS STREAM] CLIENT_DISCONNECTED: %s", client_id)

    async def clear_all(self):
        """
        Disconnects every active session.
        Intended for test tearDown to guarantee a clean state.
        """
        async with self._get_lock():
            client_ids = list(self._active_connections.keys())

        for cid in client_ids:
            await self.disconnect(cid)

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    async def subscribe_client(
        self,
        client_id: str,
        camera_id: Optional[str] = None,
        zone_id: Optional[str] = None,
        event_id: Optional[str] = "*",
    ) -> bool:
        """
        Registers a subscription for a client session after checking resource authorization.
        Returns True if authorized and registered, False if access denied.
        """
        from app.core.authorization import verify_websocket_subscription_access

        async with self._get_lock():
            session = self._active_connections.get(client_id)
            if session is None:
                return False

            if not verify_websocket_subscription_access(
                user=session.user,
                event_id=event_id or "*",
                camera_id=camera_id or "*",
                zone_id=zone_id or "*"
            ):
                logger.warning(
                    "[WS STREAM] SUBSCRIPTION_DENIED: client=%s role=%s target=(%s, %s, %s)",
                    client_id,
                    session.user.role if session.user else "none",
                    event_id,
                    camera_id,
                    zone_id,
                )
                return False

            if not camera_id or camera_id == "*":
                session.subscribe_all = True
                logger.info(
                    "[WS STREAM] SUBSCRIPTION_CREATED: %s → ALL streams", client_id
                )
            else:
                key = (event_id or "*", camera_id, zone_id or "*")
                session.subscriptions.add(key)
                logger.info(
                    "[WS STREAM] SUBSCRIPTION_CREATED: %s → %s", client_id, key
                )
            return True


    async def unsubscribe_client(self, client_id: str):
        """Clears all subscriptions for a client without disconnecting."""
        async with self._get_lock():
            session = self._active_connections.get(client_id)
            if session:
                session.subscriptions.clear()
                session.subscribe_all = False
                logger.info("[WS STREAM] SUBSCRIPTION_REMOVED: %s", client_id)

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    async def broadcast_inference_result(self, result_payload: Dict[str, Any]):
        """
        Publishes an inference result to every client subscribed to the
        matching (event_id, camera_id, zone_id) stream.

        Subscription isolation guarantee:
          CAM-01 results are never delivered to CAM-02 subscribers.

        The payload is serialised once through RealtimeInferenceResponse to
        guarantee schema conformance, then enqueued per-client.
        """
        event_id = str(result_payload.get("event_id", "evt_01"))
        camera_id = str(result_payload.get("camera_id", ""))
        zone_id = str(result_payload.get("zone_id", ""))

        # Normalise to canonical schema once
        if isinstance(result_payload, RealtimeInferenceResponse):
            export_payload = result_payload.model_dump()
        else:
            try:
                export_payload = RealtimeInferenceResponse.from_orchestrator_result(
                    result_payload
                ).model_dump()
            except Exception:
                export_payload = dict(result_payload)

        # Trigger Incident Policy evaluation failure-safely
        try:
            from app.core.database import SessionLocal
            from app.services.incident_service import process_realtime_inference_incident
            db = SessionLocal()
            try:
                process_realtime_inference_incident(db, export_payload)
            finally:
                db.close()
        except Exception as err:
            logger.warning("[WS STREAM] Non-fatal error evaluating incident policy: %s", err)

        envelope = {"type": "INFERENCE_UPDATE", "data": export_payload}

        async with self._get_lock():
            sessions = list(self._active_connections.values())

        delivered = 0
        for session in sessions:
            if not session.is_active:
                continue

            should_deliver = False
            if session.subscribe_all:
                should_deliver = True
            else:
                for sub_evt, sub_cam, sub_zone in session.subscriptions:
                    cam_match = sub_cam == camera_id or sub_cam == "*"
                    evt_match = sub_evt == "*" or sub_evt == event_id
                    zone_match = sub_zone == "*" or sub_zone == zone_id
                    if cam_match and evt_match and zone_match:
                        should_deliver = True
                        break

            if should_deliver:
                session.enqueue_payload(envelope)
                delivered += 1

        if delivered > 0:
            logger.debug(
                "[WS STREAM] INFERENCE_UPDATE_PUBLISHED: cam=%s zone=%s → %d client(s)",
                camera_id,
                zone_id,
                delivered,
            )

    async def broadcast_dispatch_update(self, dispatch_payload: Dict[str, Any]):
        """
        Publishes a dispatch status update event to connected clients.
        Envelope: {"type": "DISPATCH_UPDATE", "data": dispatch_payload}
        """
        envelope = {"type": "DISPATCH_UPDATE", "data": dispatch_payload}

        async with self._get_lock():
            sessions = list(self._active_connections.values())

        delivered = 0
        for session in sessions:
            if not session.is_active:
                continue
            session.enqueue_payload(envelope)
            delivered += 1

        logger.info("[WS STREAM] DISPATCH_UPDATE_PUBLISHED: dispatch_id=%s → %d client(s)", dispatch_payload.get("dispatch_id"), delivered)

    # ------------------------------------------------------------------
    # Stats (for health endpoint)
    # ------------------------------------------------------------------

    async def get_connection_stats(self) -> Dict[str, Any]:
        """Returns statistics on active connections and subscriptions."""
        async with self._get_lock():
            count = len(self._active_connections)
            details = [
                {
                    "client_id": s.client_id,
                    "role": s.user.role if s.user else "unknown",
                    "subscriptions_count": len(s.subscriptions),
                    "subscribe_all": s.subscribe_all,
                    "queue_size": s.queue.qsize(),
                    "is_active": s.is_active,
                }
                for s in self._active_connections.values()
            ]
        return {
            "active_connections_count": count,
            "clients": details,
        }


# Global singleton — shared across routers and the result store update path.
realtime_stream_manager = RealtimeStreamManager()
