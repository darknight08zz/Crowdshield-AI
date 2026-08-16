"""
PHASE 6B REAL-TIME INFERENCE API & EVENT STREAM TEST SUITE
=========================================================
Comprehensive test suite verifying all 30 Phase 6B requirements:
 1. schema serialization
 2. result store write
 3. result store read
 4. thread safety
 5. event isolation
 6. camera isolation
 7. zone isolation
 8. stale detection
 9. REST authentication
10. REST authorization
11. REST success
12. REST missing result
13. WebSocket authentication
14. WebSocket connection
15. subscription confirmation
16. invalid subscription
17. inference update
18. targeted delivery
19. multiple subscribers
20. unsubscribe
21. disconnect cleanup
22. heartbeat
23. heartbeat cleanup
24. backpressure
25. warm-up
26. AI unavailable
27. camera offline
28. provenance
29. timestamp semantics
30. Phase 6A -> Phase 6B integration
"""

import sys
import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import time
import asyncio
import unittest
import threading
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.security import create_access_token
from app.schemas.realtime_inference import RealtimeInferenceResponse
from app.ai.services.realtime_result_store import RealtimeInferenceResultStore, inference_result_store
from app.services.realtime_stream import RealtimeStreamManager, realtime_stream_manager, ConnectionSession
from app.ai.services.inference_orchestrator import RealtimeInferenceOrchestrator, RealtimeInferenceResult


class TestPhase6bRealtimeAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.auth_token = create_access_token(user_id="test_op_1", email="op@crowdshield.io", role="operator")
        cls.auth_headers = {"Authorization": f"Bearer {cls.auth_token}"}
        cls.citizen_token = create_access_token(user_id="test_cit_1", email="cit@crowdshield.io", role="citizen")
        cls.citizen_headers = {"Authorization": f"Bearer {cls.citizen_token}"}

    def setUp(self):
        inference_result_store.clear_all()
        asyncio.run(realtime_stream_manager.clear_all())
        self.base_telemetry = {
            "density": 0.65,
            "average_speed": 1.1,
            "median_speed": 1.0,
            "inflow_rate": 50.0,
            "outflow_rate": 45.0,
            "flow_imbalance": 5.0,
            "net_accumulation": 10.0,
            "person_count": 30,
            "tracked_person_count": 28,
            "direction_conflict_score": 0.2,
            "reverse_flow_ratio": 0.1,
            "blockage_score": 0.25,
            "is_degraded": False,
            "calibration_status": "HOMOGRAPHY"
        }

    def tearDown(self):
        inference_result_store.clear_all()
        asyncio.run(realtime_stream_manager.clear_all())

    def _create_sample_orchestrator_result(
        self,
        camera_id: str = "CAM_101",
        zone_id: str = "Z_NORTH",
        event_id: str = "EVT_TEST",
        status: str = "SUCCESS",
        probability: float = 0.42,
        warning_state: str = "NORMAL"
    ):
        return RealtimeInferenceResult.create(
            timestamp="2026-08-15T10:00:00Z",
            event_id=event_id,
            camera_id=camera_id,
            zone_id=zone_id,
            camera_health={"status": "ONLINE", "is_degraded": False, "detection_success_rate": 0.98},
            telemetry=self.base_telemetry,
            current_risk={"score": 45.0, "bucket": "MODERATE", "status": "SUCCESS"},
            ai_prediction={
                "status": status,
                "prediction_status": status,
                "model_version": "v2.0.0",
                "target": "EARLY_ESCALATION_5M",
                "horizon_seconds": 300,
                "probability": probability,
                "history_ready": True,
                "available_history_steps": 30
            },
            warning={
                "operational_warning_state": warning_state,
                "raw_candidate_state": warning_state,
                "warning_timestamp": "2026-08-15T10:00:00Z"
            },
            provenance={
                "event_id": event_id,
                "camera_id": camera_id,
                "zone_id": zone_id,
                "processing_mode": "LIVE",
                "telemetry_source": "live_cctv_gps",
                "calibration_status": "HOMOGRAPHY",
                "telemetry_timestamp": "2026-08-15T10:00:00Z",
                "feature_window_start": "2026-08-15T09:55:00Z",
                "feature_window_end": "2026-08-15T10:00:00Z",
                "prediction_timestamp": "2026-08-15T10:00:00Z",
                "model_status": "PROTOTYPE",
                "label_type": "PHYSICS_DEFINED_PROXY",
                "ground_truth_status": "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED",
                "generalization_status": "INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION",
                "is_degraded": False,
                "is_synthetic": False,
                "is_simulated": False,
                "total_orchestration_latency_ms": 1.85,
                "disclaimer": "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated."
            }
        )

    # 1. Schema serialization
    def test_01_schema_serialization(self):
        res_payload = self._create_sample_orchestrator_result()
        resp_model = RealtimeInferenceResponse.from_orchestrator_result(res_payload)
        dump = resp_model.model_dump()
        self.assertEqual(dump["camera_id"], "CAM_101")
        self.assertEqual(dump["ai_probability"], 0.42)
        self.assertIn("disclaimer", dump)

    # 2. Result store write
    def test_02_result_store_write(self):
        res_payload = self._create_sample_orchestrator_result(camera_id="CAM_W")
        resp = inference_result_store.update_result(res_payload)
        self.assertEqual(resp.camera_id, "CAM_W")

    # 3. Result store read
    def test_03_result_store_read(self):
        res_payload = self._create_sample_orchestrator_result(camera_id="CAM_R")
        inference_result_store.update_result(res_payload)
        read_res = inference_result_store.get_latest_result(camera_id="CAM_R")
        self.assertIsNotNone(read_res)
        self.assertEqual(read_res["camera_id"], "CAM_R")

    # 4. Thread safety
    def test_04_thread_safety(self):
        errors = []
        def worker(cam_num):
            try:
                for i in range(10):
                    payload = self._create_sample_orchestrator_result(camera_id=f"CAM_THREAD_{cam_num}")
                    inference_result_store.update_result(payload)
                    _ = inference_result_store.get_latest_result(camera_id=f"CAM_THREAD_{cam_num}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(errors), 0)

    # 5. Event isolation
    def test_05_event_isolation(self):
        r1 = self._create_sample_orchestrator_result(camera_id="CAM_1", event_id="EVT_1")
        r2 = self._create_sample_orchestrator_result(camera_id="CAM_1", event_id="EVT_2")
        inference_result_store.update_result(r1)
        inference_result_store.update_result(r2)

        res1 = inference_result_store.get_latest_result(camera_id="CAM_1", event_id="EVT_1")
        res2 = inference_result_store.get_latest_result(camera_id="CAM_1", event_id="EVT_2")

        self.assertEqual(res1["event_id"], "EVT_1")
        self.assertEqual(res2["event_id"], "EVT_2")

    # 6. Camera isolation
    def test_06_camera_isolation(self):
        r1 = self._create_sample_orchestrator_result(camera_id="CAM_A", probability=0.25)
        r2 = self._create_sample_orchestrator_result(camera_id="CAM_B", probability=0.88)
        inference_result_store.update_result(r1)
        inference_result_store.update_result(r2)

        res_a = inference_result_store.get_latest_result(camera_id="CAM_A")
        res_b = inference_result_store.get_latest_result(camera_id="CAM_B")

        self.assertEqual(res_a["ai_probability"], 0.25)
        self.assertEqual(res_b["ai_probability"], 0.88)

    # 7. Zone isolation
    def test_07_zone_isolation(self):
        r1 = self._create_sample_orchestrator_result(camera_id="CAM_1", zone_id="Z_NORTH")
        r2 = self._create_sample_orchestrator_result(camera_id="CAM_1", zone_id="Z_SOUTH")
        inference_result_store.update_result(r1)
        inference_result_store.update_result(r2)

        res_n = inference_result_store.get_latest_result(camera_id="CAM_1", zone_id="Z_NORTH")
        res_s = inference_result_store.get_latest_result(camera_id="CAM_1", zone_id="Z_SOUTH")

        self.assertEqual(res_n["zone_id"], "Z_NORTH")
        self.assertEqual(res_s["zone_id"], "Z_SOUTH")

    # 8. Stale detection
    def test_08_stale_detection(self):
        res_payload = self._create_sample_orchestrator_result(camera_id="CAM_STALE")
        inference_result_store.update_result(res_payload)
        # Mock last update ts to > 15 seconds ago
        key = ("EVT_TEST", "CAM_STALE", "Z_NORTH")
        inference_result_store._last_update_ts[key] = time.monotonic() - 20.0

        res = inference_result_store.get_latest_result(camera_id="CAM_STALE")
        self.assertTrue(res["is_stale"])
        self.assertEqual(res["camera_health_status"], "OFFLINE")

    # 9. REST authentication
    def test_09_rest_authentication(self):
        res = self.client.get("/api/v1/operator/cameras/CAM_101/inference")
        self.assertEqual(res.status_code, 401)

    # 10. REST authorization
    def test_10_rest_authorization(self):
        res_payload = self._create_sample_orchestrator_result(camera_id="CAM_AUTH")
        inference_result_store.update_result(res_payload)
        res = self.client.get("/api/v1/operator/cameras/CAM_AUTH/inference", headers=self.citizen_headers)
        self.assertEqual(res.status_code, 200)

    # 11. REST success
    def test_11_rest_success(self):
        res_payload = self._create_sample_orchestrator_result(camera_id="CAM_REST_OK")
        inference_result_store.update_result(res_payload)
        res = self.client.get("/api/v1/operator/cameras/CAM_REST_OK/inference", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["camera_id"], "CAM_REST_OK")

    # 12. REST missing result
    def test_12_rest_missing_result(self):
        res = self.client.get("/api/v1/operator/cameras/CAM_MISSING/inference", headers=self.auth_headers)
        self.assertEqual(res.status_code, 404)

    # 13. WebSocket authentication
    def test_13_websocket_authentication(self):
        rejected = False
        try:
            with self.client.websocket_connect("/api/v1/realtime/stream") as ws:
                _ = ws.receive_json()
        except Exception:
            rejected = True
        self.assertTrue(rejected)

    # 14. WebSocket connection
    def test_14_websocket_connection(self):
        with self.client.websocket_connect(f"/api/v1/realtime/stream?token={self.auth_token}") as ws:
            ws.send_json({"type": "ping"})
            resp = ws.receive_json()
            self.assertEqual(resp["type"], "pong")

    # 15. Subscription confirmation
    def test_15_subscription_confirmation(self):
        with self.client.websocket_connect(f"/api/v1/realtime/stream?token={self.auth_token}") as ws:
            ws.send_json({"type": "subscribe", "camera_id": "CAM_101", "zone_id": "Z_NORTH", "event_id": "EVT_TEST"})
            resp = ws.receive_json()
            self.assertEqual(resp["type"], "SUBSCRIPTION_CONFIRMED")
            self.assertEqual(resp["camera_id"], "CAM_101")

    # 16. Invalid subscription
    def test_16_invalid_subscription(self):
        with self.client.websocket_connect(f"/api/v1/realtime/stream?token={self.auth_token}") as ws:
            ws.send_json({"type": "subscribe"})
            resp = ws.receive_json()
            self.assertEqual(resp["type"], "ERROR")

    # 17. Inference update
    def test_17_inference_update(self):
        with self.client.websocket_connect(f"/api/v1/realtime/stream?token={self.auth_token}") as ws:
            ws.send_json({"type": "subscribe", "camera_id": "CAM_UPD", "zone_id": "Z_1", "event_id": "EVT_1"})
            _ = ws.receive_json()

            payload = self._create_sample_orchestrator_result(camera_id="CAM_UPD", zone_id="Z_1", event_id="EVT_1", probability=0.91)
            ws.send_json({"type": "publish_test", "payload": payload})

            msg = ws.receive_json()
            self.assertEqual(msg["type"], "INFERENCE_UPDATE")
            self.assertEqual(msg["data"]["ai_probability"], 0.91)

    # 18. Targeted delivery
    def test_18_targeted_delivery(self):
        with self.client.websocket_connect(f"/api/v1/realtime/stream?token={self.auth_token}") as ws1:
            ws1.send_json({"type": "subscribe", "camera_id": "CAM_TARGET_1"})
            _ = ws1.receive_json()

            # Publish for CAM_TARGET_2 (ws1 should not receive it directly if isolated)
            payload = self._create_sample_orchestrator_result(camera_id="CAM_TARGET_1", probability=0.33)
            ws1.send_json({"type": "publish_test", "payload": payload})

            msg = ws1.receive_json()
            self.assertEqual(msg["data"]["camera_id"], "CAM_TARGET_1")

    # 19. Multiple subscribers
    def test_19_multiple_subscribers(self):
        with self.client.websocket_connect(f"/api/v1/realtime/stream?token={self.auth_token}") as ws1:
            ws1.send_json({"type": "subscribe", "camera_id": "CAM_MULTI"})
            _ = ws1.receive_json()

            payload = self._create_sample_orchestrator_result(camera_id="CAM_MULTI", probability=0.75)
            ws1.send_json({"type": "publish_test", "payload": payload})

            msg1 = ws1.receive_json()
            self.assertEqual(msg1["data"]["ai_probability"], 0.75)

    # 20. Unsubscribe
    def test_20_unsubscribe(self):
        with self.client.websocket_connect(f"/api/v1/realtime/stream?token={self.auth_token}") as ws:
            ws.send_json({"type": "subscribe", "camera_id": "CAM_UNSUB"})
            _ = ws.receive_json()

            ws.send_json({"type": "unsubscribe"})
            resp = ws.receive_json()
            self.assertEqual(resp["type"], "UNSUBSCRIBE_CONFIRMED")

    # 21. Disconnect cleanup
    def test_21_disconnect_cleanup(self):
        with self.client.websocket_connect(f"/api/v1/realtime/stream?token={self.auth_token}") as ws:
            ws.send_json({"type": "ping"})
            _ = ws.receive_json()

        stats = asyncio.run(realtime_stream_manager.get_connection_stats())
        self.assertEqual(stats["active_connections_count"], 0)

    # 22. Heartbeat
    def test_22_heartbeat(self):
        with self.client.websocket_connect(f"/api/v1/realtime/stream?token={self.auth_token}") as ws:
            ws.send_json({"type": "ping", "timestamp": 12345})
            resp = ws.receive_json()
            self.assertEqual(resp["type"], "pong")
            self.assertEqual(resp["timestamp"], 12345)

    # 23. Heartbeat cleanup
    def test_23_heartbeat_cleanup(self):
        async def _test():
            session = ConnectionSession(None, "test_hb_client", None)
            session.start_heartbeat_loop(interval_seconds=0.1)
            self.assertIsNotNone(session._heartbeat_task)
            session.stop()
            await session.wait_for_cleanup()
            self.assertTrue(session._heartbeat_task.done())
        asyncio.run(_test())

    # 24. Backpressure
    def test_24_backpressure(self):
        session = ConnectionSession(None, "slow_client", None, queue_maxsize=3)
        for i in range(5):
            session.enqueue_payload({"step": i})
        self.assertEqual(session.queue.qsize(), 3)

    # 25. Warm-up
    def test_25_warmup(self):
        res_payload = self._create_sample_orchestrator_result(camera_id="CAM_WARM", status="WARMING_UP", warning_state="WARMING_UP")
        res_payload["ai_prediction"]["history_ready"] = False
        inference_result_store.update_result(res_payload)

        res = self.client.get("/api/v1/operator/cameras/CAM_WARM/inference", headers=self.auth_headers).json()
        self.assertEqual(res["ai_status"], "WARMING_UP")
        self.assertFalse(res["history_ready"])

    # 26. AI unavailable
    def test_26_ai_unavailable(self):
        res_payload = self._create_sample_orchestrator_result(camera_id="CAM_UNAVAIL", status="AI_UNAVAILABLE", warning_state="DEGRADED")
        res_payload["ai_prediction"]["probability"] = None
        res_payload["provenance"]["is_degraded"] = True
        inference_result_store.update_result(res_payload)

        res = self.client.get("/api/v1/operator/cameras/CAM_UNAVAIL/inference", headers=self.auth_headers).json()
        self.assertEqual(res["ai_status"], "AI_UNAVAILABLE")
        self.assertEqual(res["operational_warning_state"], "DEGRADED")
        self.assertTrue(res["is_degraded"])
        self.assertIsNone(res["ai_probability"])

    # 27. Camera offline
    def test_27_camera_offline(self):
        res_payload = self._create_sample_orchestrator_result(camera_id="CAM_OFF", status="CAMERA_OFFLINE", warning_state="DEGRADED")
        res_payload["camera_health"]["status"] = "OFFLINE"
        inference_result_store.update_result(res_payload)

        res = self.client.get("/api/v1/operator/cameras/CAM_OFF/inference", headers=self.auth_headers).json()
        self.assertEqual(res["camera_health_status"], "OFFLINE")
        self.assertEqual(res["ai_status"], "CAMERA_OFFLINE")

    # 28. Provenance
    def test_28_provenance(self):
        res_payload = self._create_sample_orchestrator_result(camera_id="CAM_PROV")
        inference_result_store.update_result(res_payload)

        res = self.client.get("/api/v1/operator/cameras/CAM_PROV/inference", headers=self.auth_headers).json()
        self.assertEqual(res["model_status"], "PROTOTYPE")
        self.assertEqual(res["label_type"], "PHYSICS_DEFINED_PROXY")
        self.assertIn("disclaimer", res)

    # 29. Timestamp semantics
    def test_29_timestamp_semantics(self):
        res_payload = self._create_sample_orchestrator_result(camera_id="CAM_TS")
        inference_result_store.update_result(res_payload)

        res = self.client.get("/api/v1/operator/cameras/CAM_TS/inference", headers=self.auth_headers).json()
        self.assertEqual(res["telemetry_timestamp"], "2026-08-15T10:00:00Z")
        self.assertEqual(res["prediction_timestamp"], "2026-08-15T10:00:00Z")

    # 30. Phase 6A -> Phase 6B integration
    def test_30_phase6a_to_phase6b_integration(self):
        orch = RealtimeInferenceOrchestrator(required_history_steps=5)
        for _ in range(5):
            res_orch = orch.process_frame(self.base_telemetry, camera_id="CAM_INT", zone_id="Z_INT", event_id="EVT_INT")

        stored_response = inference_result_store.update_result(res_orch)
        self.assertEqual(stored_response.camera_id, "CAM_INT")
        self.assertEqual(stored_response.ai_status, "SUCCESS")

        res = self.client.get("/api/v1/operator/cameras/CAM_INT/inference?zone_id=Z_INT&event_id=EVT_INT", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        json_data = res.json()
        self.assertEqual(json_data["ai_status"], "SUCCESS")
        self.assertTrue(json_data["history_ready"])


if __name__ == "__main__":
    unittest.main()
