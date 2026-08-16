# CrowdShield Phase 6B — Real-Time Inference API & Event Stream Architecture

## Executive Summary
Phase 6B delivers a production-grade, thread-safe REST and WebSocket API for streaming computer vision and physics inference results from Phase 6A (`RealtimeInferenceResult`) to control room operators, field officers, and citizen applications without touching or modifying the underlying CV models, tracking logic, or orchestrator contracts.

---

## Architectural Topology

```
+-------------------------------------------------------+
|        Phase 6A Inference Pipeline & Engine          |
|  (YOLOv8 + ByteTrack + Temporal Model + EarlyWarning) |
+-------------------------------------------------------+
                           |
                           v  update_result(payload)
+-------------------------------------------------------+
|           RealtimeInferenceResultStore                |
|  - Keyed by (event_id, camera_id, zone_id)            |
|  - Thread-safe memory cache & 15s stale detector       |
+-------------------------------------------------------+
             /                           \
            /                             \  broadcast_inference_result()
           v                               v
+-----------------------+     +-----------------------------------+
|   FastAPI REST API    |     |      RealtimeStreamManager        |
| GET /cameras/{id}/... |     | WS /api/v1/realtime/stream       |
+-----------------------+     +-----------------------------------+
           |                                |
           v                                v
+-------------------------------------------------------+
|  Operators, Field Officers, Mobile & Web Clients      |
+-------------------------------------------------------+
```

---

## Component Architecture

### 1. Canonical Schema (`app/schemas/realtime_inference.py`)
- Standardizes output serialization for both REST snapshots and WebSocket frames.
- Strictly separates physical risk scores (`current_risk_score`) from AI predictions (`ai_probability`).
- Preserves full provenance, data quality indicators, and legal disclaimers.

### 2. Thread-Safe Store (`app/ai/services/realtime_result_store.py`)
- Keyed by `(event_id, camera_id, zone_id)`.
- Monotonic wall-clock timestamp tracking for staleness detection.
- Automatically flags outputs older than 15.0 seconds as `is_stale=true` and `camera_health_status="OFFLINE"`.
- Does NOT mutate stored historical data on read.

### 3. Pub-Sub Manager (`app/services/realtime_stream.py`)
- Manages active client WebSocket connections with JWT authentication via query string `?token=...`.
- Employs bounded per-client queues (`maxsize=10`) with backpressure drop policy (oldest payload dropped when queue is full).
- Uses sentinel-based task termination for deterministic cleanup without task or memory leaks.

### 4. API Endpoints (`app/api/v1/realtime.py`)
- `GET /api/v1/operator/cameras/{camera_id}/inference`: Returns snapshot for specified camera.
- `GET /api/v1/operator/cameras/{camera_id}/zones/{zone_id}/inference`: Returns zone-specific snapshot.
- `WS /api/v1/realtime/stream`: Pub-sub WebSocket channel supporting `subscribe`, `unsubscribe`, `ping`, and streaming update envelopes.
- `GET /api/v1/realtime/health`: Delivery health probe and WebSocket connection statistics.

---

## WebSocket Client Usage Example

```javascript
const token = "YOUR_JWT_TOKEN";
const ws = new WebSocket(`wss://api.crowdshield.io/api/v1/realtime/stream?token=${token}`);

ws.onopen = () => {
  // Subscribe to specific camera & zone
  ws.send(JSON.stringify({
    type: "subscribe",
    camera_id: "CAM-01",
    zone_id: "ZONE-NORTH",
    event_id: "EVT-MAIN"
  }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === "INFERENCE_UPDATE") {
    console.log("Realtime Inference Payload:", msg.data);
  }
};
```

---

## Performance & Test Verification
- **Test Suite**: 30 automated tests in `tests/test_phase6b_realtime_api.py`.
- **Backend Suite**: 158 total automated backend tests passing deterministically.
- **Execution Time**: ~4.4s for Phase 6B suite; ~20.5s for full backend suite.
- **Resource Safety**: Thread locks & OpenBLAS thread limits (`OMP_NUM_THREADS=1`) configured via `pytest.ini`.
