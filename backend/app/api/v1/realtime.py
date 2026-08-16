"""
CROWDSHIELD REALTIME INFERENCE API & WEBSOCKET ROUTER (PHASE 6B)
================================================================
FastAPI routes exposing the Phase 6B delivery layer:

  REST:
    GET  /api/v1/operator/cameras/{camera_id}/inference
    GET  /api/v1/operator/cameras/{camera_id}/zones/{zone_id}/inference

  WebSocket:
    WS   /api/v1/realtime/stream

  Health:
    GET  /api/v1/realtime/health

Security:
  - All REST endpoints require a valid JWT Bearer token.
  - WebSocket authentication is via ?token=<JWT> query parameter.
  - No credentials are returned or logged.
  - Stack traces are never exposed in error responses.

REST endpoints read from the thread-safe InferenceResultStore.
They do NOT trigger the YOLO/AI pipeline.
"""

import json
import logging
from typing import Optional, Dict, Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from app.core.security import require_role
from app.schemas.realtime_inference import RealtimeInferenceResponse
from app.ai.services.realtime_result_store import inference_result_store
from app.services.realtime_stream import realtime_stream_manager, ConnectionSession

logger = logging.getLogger("crowdshield.api.realtime")

router = APIRouter(tags=["Real-Time AI Inference"])

# ---------------------------------------------------------------------------
# REST — Latest Inference Snapshot
# ---------------------------------------------------------------------------

_REST_AUTH = [
    Depends(
        require_role(
            "operator", "event_admin", "system_admin", "field_officer", "citizen"
        )
    )
]


@router.get(
    "/operator/cameras/{camera_id}/inference",
    response_model=Dict[str, Any],
    dependencies=_REST_AUTH,
    summary="Latest inference snapshot for a camera",
    description=(
        "Returns the latest RealtimeInferenceResult for the specified camera. "
        "Reads from the in-memory result store — does NOT trigger YOLO/AI inference. "
        "If the result is older than the configured stale threshold, "
        "is_stale=true is included in the response."
    ),
)
async def get_latest_camera_inference(
    camera_id: str,
    zone_id: Optional[str] = Query(None, description="Optional zone filter"),
    event_id: Optional[str] = Query(None, description="Optional event filter"),
):
    """
    Possible responses:
      200 — latest result (may include is_stale=true)
      401 — not authenticated
      403 — not authorised
      404 — no result available for this camera
    """
    result = inference_result_store.get_latest_result(
        camera_id=camera_id,
        zone_id=zone_id,
        event_id=event_id,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No inference result available for camera_id='{camera_id}'.",
        )

    return result


@router.get(
    "/operator/cameras/{camera_id}/zones/{zone_id}/inference",
    response_model=Dict[str, Any],
    dependencies=_REST_AUTH,
    summary="Latest inference snapshot for a specific camera zone",
    description=(
        "Zone-specific variant of the camera inference endpoint. "
        "Enforces that only the (camera_id, zone_id) stream is returned."
    ),
)
async def get_latest_zone_inference(
    camera_id: str,
    zone_id: str,
    event_id: Optional[str] = Query(None, description="Optional event filter"),
):
    """
    Possible responses:
      200 — latest result
      401 — not authenticated
      403 — not authorised
      404 — no result for this camera/zone
    """
    result = inference_result_store.get_latest_result(
        camera_id=camera_id,
        zone_id=zone_id,
        event_id=event_id,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No inference result available for "
                f"camera_id='{camera_id}', zone_id='{zone_id}'."
            ),
        )

    return result


# ---------------------------------------------------------------------------
# WebSocket — Real-Time Stream
# ---------------------------------------------------------------------------

@router.websocket("/realtime/stream")
async def realtime_inference_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT Bearer Token"),
):
    """
    WebSocket real-time inference stream.

    Protocol:
      1. Connect:     WS /api/v1/realtime/stream?token=<JWT>
      2. Subscribe:   {"type": "subscribe", "camera_id": "CAM-01",
                        "zone_id": "ZONE-A", "event_id": "evt_01"}
      3. Receive:     {"type": "INFERENCE_UPDATE", "data": { ... }}
      4. Heartbeat:   {"type": "ping"} → {"type": "pong"}
      5. Unsubscribe: {"type": "unsubscribe"}
      6. Disconnect:  close connection

    Lifecycle guarantee:
      On disconnect (normal or abnormal), all background tasks (sender,
      heartbeat) are cancelled and awaited before the session is removed.
    """
    session: Optional[ConnectionSession] = await realtime_stream_manager.connect(
        websocket, token=token
    )
    if session is None:
        return  # Authentication failed; WebSocket already closed

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                await websocket.send_json(
                    {"type": "ERROR", "detail": "Invalid JSON payload."}
                )
                continue

            msg_type = str(msg.get("type", "")).lower()

            if msg_type == "subscribe":
                cam_id = msg.get("camera_id")
                z_id = msg.get("zone_id")
                e_id = msg.get("event_id", "*")

                if not cam_id:
                    await websocket.send_json(
                        {
                            "type": "ERROR",
                            "detail": "subscribe requires camera_id.",
                        }
                    )
                    continue

                success = await realtime_stream_manager.subscribe_client(
                    client_id=session.client_id,
                    camera_id=cam_id,
                    zone_id=z_id,
                    event_id=e_id,
                )
                if not success:
                    await websocket.send_json(
                        {
                            "type": "ERROR",
                            "code": 403,
                            "detail": "Unauthorized subscription to requested resource scope.",
                        }
                    )
                    continue

                await websocket.send_json(
                    {
                        "type": "SUBSCRIPTION_CONFIRMED",
                        "event_id": e_id,
                        "camera_id": cam_id,
                        "zone_id": z_id,
                    }
                )

            elif msg_type == "unsubscribe":
                await realtime_stream_manager.unsubscribe_client(session.client_id)
                await websocket.send_json({"type": "UNSUBSCRIBE_CONFIRMED"})

            elif msg_type == "ping":
                await websocket.send_json(
                    {"type": "pong", "timestamp": msg.get("timestamp")}
                )

            elif msg_type == "publish_test":
                # Test-only: allows the test client to trigger a broadcast
                # without needing a separate thread.
                payload = msg.get("payload", {})
                await realtime_stream_manager.broadcast_inference_result(payload)

            else:
                await websocket.send_json(
                    {
                        "type": "ERROR",
                        "detail": f"Unknown message type '{msg.get('type')}'.",
                    }
                )

    except WebSocketDisconnect:
        logger.info("[WS ROUTER] Client disconnected normally: %s", session.client_id)
    except Exception as exc:
        logger.warning(
            "[WS ROUTER] Exception on socket %s: %s", session.client_id, exc
        )
    finally:
        await realtime_stream_manager.disconnect(session.client_id)


# ---------------------------------------------------------------------------
# Health Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/realtime/health",
    dependencies=[
        Depends(require_role("operator", "event_admin", "system_admin"))
    ],
    summary="Real-time delivery service health status",
)
async def get_realtime_service_health():
    """
    Reports the operational health of the Phase 6B delivery layer.

    Includes:
      - Active WebSocket connection count and subscription details.
      - Active inference streams and their freshness status.

    Does NOT claim "healthy" merely because FastAPI is running.
    Status is DEGRADED if no active streams are present and connections exist.
    """
    ws_stats = await realtime_stream_manager.get_connection_stats()
    active_streams = inference_result_store.list_active_streams()

    stale_streams = [s for s in active_streams if s.get("is_stale")]
    fresh_streams = [s for s in active_streams if not s.get("is_stale")]

    # Determine meaningful health status
    conn_count = ws_stats.get("active_connections_count", 0)
    if len(stale_streams) > 0 and len(fresh_streams) == 0:
        service_status = "DEGRADED"
    else:
        service_status = "HEALTHY"

    return {
        "service": "RealtimeInferenceDeliveryService",
        "status": service_status,
        "active_streams_count": len(active_streams),
        "fresh_streams_count": len(fresh_streams),
        "stale_streams_count": len(stale_streams),
        "active_streams": active_streams,
        "websocket": ws_stats,
    }
