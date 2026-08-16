"""
CROWDSHIELD REAL-TIME INFERENCE RESPONSE SCHEMAS (PHASE 6B)
===========================================================
Canonical Pydantic response models for RealtimeInferenceResult.
Exposes identity, timestamps, camera status, CV metrics, current physics risk,
v2.0.0 AI predictions, operational alert states, quality indicators, and explicit provenance.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class IdentitySchema(BaseModel):
    event_id: str = Field(default="evt_01", description="Event identifier")
    camera_id: str = Field(..., description="Camera identifier")
    zone_id: str = Field(..., description="Zone identifier")


class TimestampsSchema(BaseModel):
    telemetry_timestamp: str = Field(..., description="ISO 8601 UTC timestamp of frame telemetry generation")
    feature_window_start: Optional[str] = Field(None, description="ISO 8601 UTC timestamp of temporal feature window start")
    feature_window_end: Optional[str] = Field(None, description="ISO 8601 UTC timestamp of temporal feature window end")
    prediction_timestamp: str = Field(..., description="ISO 8601 UTC timestamp of AI model execution")
    warning_timestamp: Optional[str] = Field(None, description="ISO 8601 UTC timestamp of EarlyWarningEngine state change")


class CameraStateSchema(BaseModel):
    status: str = Field("ONLINE", description="Camera health status: ONLINE, DEGRADED, OFFLINE, CV_UNAVAILABLE")
    processing_mode: str = Field("LIVE", description="Processing mode: LIVE, REPLAY, SIMULATION")
    telemetry_source: str = Field("live_cctv_gps", description="Source of telemetry data")
    is_degraded: bool = Field(False, description="Flag indicating degraded camera feed or vision pipeline")


class CVTelemetrySchema(BaseModel):
    person_count: int = Field(0, description="Instantaneous detected person count")
    tracked_person_count: int = Field(0, description="Active ByteTrack tracked person count")
    density: float = Field(0.0, description="Instantaneous crowd density (people/m^2)")
    average_speed: float = Field(1.2, description="Mean pedestrian speed (m/s)")
    median_speed: float = Field(1.1, description="Median pedestrian speed (m/s)")
    inflow_rate: float = Field(0.0, description="Pedestrians entering per minute")
    outflow_rate: float = Field(0.0, description="Pedestrians exiting per minute")
    flow_imbalance: float = Field(0.0, description="Inflow - Outflow differential")
    net_accumulation: float = Field(0.0, description="Cumulative accumulation rate")
    direction_conflict_score: float = Field(0.0, description="Directional vector conflict ratio (0.0 - 1.0)")
    reverse_flow_ratio: float = Field(0.0, description="Reverse motion vector ratio (0.0 - 1.0)")
    blockage_score: float = Field(0.0, description="Egress bottleneck blockage score (0.0 - 1.0)")


class CurrentRiskSchema(BaseModel):
    status: str = Field("SUCCESS", description="Risk calculation status")
    current_risk: float = Field(0.0, description="Phase 3 ground truth physics risk score (0.0 - 100.0)")
    current_risk_level: str = Field("LOW", description="Risk bucket: LOW, MODERATE, HIGH, CRITICAL")
    factors: Dict[str, Any] = Field(default_factory=dict, description="Risk contributor breakdown")


class AIPredictionSchema(BaseModel):
    status: str = Field("SUCCESS", description="AI prediction status: SUCCESS, WARMING_UP, AI_UNAVAILABLE, CAMERA_OFFLINE")
    prediction_status: str = Field("SUCCESS", description="Detailed prediction status code")
    model_version: str = Field("v2.0.0", description="AI model version identifier")
    target: str = Field("EARLY_ESCALATION_5M", description="Prediction target name")
    target_version: str = Field("v1.0.0", description="Target definition schema version")
    horizon_seconds: int = Field(300, description="Prediction horizon in seconds (5 minutes)")
    ai_probability: Optional[float] = Field(None, description="Forecast escalation probability (0.0 - 1.0)")
    history_ready: bool = Field(False, description="Flag indicating if required temporal history window (30 steps) is populated")
    available_history_steps: int = Field(0, description="Current populated history window step count")
    required_history_steps: int = Field(30, description="Required history window step count for temporal inference")
    explainability: Dict[str, Any] = Field(default_factory=dict, description="SHAP feature importances and risk drivers")


class WarningStateSchema(BaseModel):
    operational_warning_state: str = Field("NORMAL", description="EarlyWarningEngine operational state: NORMAL, WATCH, EARLY_WARNING, HIGH_RISK, WARMING_UP, DEGRADED")
    raw_candidate_state: str = Field("NORMAL", description="Unpersisted candidate state")
    warning_reason: Optional[str] = Field(None, description="Reason for warning state escalation")
    persistence_count: int = Field(0, description="Current consecutive step persistence count")
    warning_timestamp: Optional[str] = Field(None, description="Timestamp of warning state transition")


class QualitySchema(BaseModel):
    calibration_status: str = Field("UNCALIBRATED", description="Homography calibration status")
    confidence_score: float = Field(1.0, description="Overall telemetry confidence score (0.0 - 1.0)")
    data_quality: str = Field("HIGH", description="Data quality rating: HIGH, MEDIUM, LOW, DEGRADED")
    is_degraded: bool = Field(False, description="Quality degradation flag")


class ProvenanceSchema(BaseModel):
    model_status: str = Field("PROTOTYPE", description="Model provenance status")
    label_type: str = Field("PHYSICS_DEFINED_PROXY", description="Ground truth label origin")
    ground_truth_status: str = Field("NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED", description="Clinical/operational validation status")
    generalization_status: str = Field("INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION", description="Generalization status")
    disclaimer: str = Field(
        "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.",
        description="Mandatory system safety disclaimer"
    )
    is_degraded: bool = Field(False, description="System degradation flag")
    is_synthetic: bool = Field(False, description="Synthetic data flag")
    is_simulated: bool = Field(False, description="Simulation mode flag")
    total_orchestration_latency_ms: float = Field(0.0, description="Backend orchestration latency in milliseconds")


class RealtimeInferenceResponse(BaseModel):
    """
    Canonical response contract for RealtimeInferenceResult exposed via REST & WebSockets.
    """
    timestamp: str = Field(..., description="ISO 8601 UTC execution timestamp")
    event_id: str = Field("evt_01", description="Event ID")
    camera_id: str = Field(..., description="Camera ID")
    zone_id: str = Field(..., description="Zone ID")

    # Grouped Payloads
    camera_health: Dict[str, Any] = Field(..., description="Camera operational health metadata")
    telemetry: Dict[str, Any] = Field(..., description="CV perception telemetry metrics")
    current_risk: Dict[str, Any] = Field(..., description="Phase 3 physics ground truth risk score")
    ai_prediction: Dict[str, Any] = Field(..., description="Phase 5 v2.0.0 temporal AI model output")
    warning: Dict[str, Any] = Field(..., description="EarlyWarningEngine operational decision output")
    provenance: Dict[str, Any] = Field(..., description="Provenance disclaimers and performance metrics")

    # Canonical Flattened Convenience Aliases (Section 2 Prompt Contract)
    telemetry_timestamp: str = Field(..., description="Telemetry timestamp")
    feature_window_start: Optional[str] = Field(None, description="Feature window start timestamp")
    feature_window_end: Optional[str] = Field(None, description="Feature window end timestamp")
    prediction_timestamp: str = Field(..., description="AI prediction timestamp")
    warning_timestamp: Optional[str] = Field(None, description="Warning timestamp")

    camera_health_status: str = Field("ONLINE", description="Camera health status string")
    processing_mode: str = Field("LIVE", description="Processing mode")
    telemetry_source: str = Field("live_cctv_gps", description="Telemetry source")

    person_count: int = Field(0, description="Person count")
    tracked_person_count: int = Field(0, description="Tracked person count")
    density: float = Field(0.0, description="Density")
    average_speed: float = Field(1.2, description="Average speed")
    median_speed: float = Field(1.1, description="Median speed")
    inflow_rate: float = Field(0.0, description="Inflow rate")
    outflow_rate: float = Field(0.0, description="Outflow rate")
    flow_imbalance: float = Field(0.0, description="Flow imbalance")
    net_accumulation: float = Field(0.0, description="Net accumulation")
    direction_conflict_score: float = Field(0.0, description="Direction conflict score")
    reverse_flow_ratio: float = Field(0.0, description="Reverse flow ratio")
    blockage_score: float = Field(0.0, description="Blockage score")

    current_physics_risk: float = Field(0.0, description="Instantaneous physics risk score (0-100)")
    current_risk_level: str = Field("LOW", description="Physics risk bucket (LOW/MODERATE/HIGH/CRITICAL)")

    model_version: str = Field("v2.0.0", description="Model version")
    target: str = Field("EARLY_ESCALATION_5M", description="Prediction target")
    target_version: str = Field("v1.0.0", description="Target version")
    horizon_seconds: int = Field(300, description="Prediction horizon seconds")
    ai_status: str = Field("SUCCESS", description="AI status string")
    ai_probability: Optional[float] = Field(None, description="AI probability")
    history_ready: bool = Field(False, description="History ready flag")

    operational_warning_state: str = Field("NORMAL", description="Operational warning state")
    warning_reason: Optional[str] = Field(None, description="Warning escalation reason")
    persistence_count: int = Field(0, description="Persistence count")

    calibration_status: str = Field("UNCALIBRATED", description="Calibration status")
    confidence_score: float = Field(1.0, description="Confidence score")
    data_quality: str = Field("HIGH", description="Data quality string")
    is_degraded: bool = Field(False, description="Is degraded flag")

    model_status: str = Field("PROTOTYPE", description="Model status")
    label_type: str = Field("PHYSICS_DEFINED_PROXY", description="Label type")
    ground_truth_status: str = Field("NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED", description="Ground truth status")
    generalization_status: str = Field("INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION", description="Generalization status")
    disclaimer: str = Field(
        "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.",
        description="Safety disclaimer"
    )

    @classmethod
    def from_orchestrator_result(cls, res: Dict[str, Any]) -> "RealtimeInferenceResponse":
        """Constructs canonical RealtimeInferenceResponse from RealtimeInferenceResult dict."""
        cam_h = res.get("camera_health", {})
        telem = res.get("telemetry", {})
        c_risk = res.get("current_risk", {})
        ai_pred = res.get("ai_prediction", {})
        warn = res.get("warning", {})
        prov = res.get("provenance", {})

        return cls(
            timestamp=res.get("timestamp", prov.get("telemetry_timestamp", "")),
            event_id=res.get("event_id", prov.get("event_id", "evt_01")),
            camera_id=res.get("camera_id", prov.get("camera_id", "")),
            zone_id=res.get("zone_id", prov.get("zone_id", "")),
            camera_health=cam_h,
            telemetry=telem,
            current_risk=c_risk,
            ai_prediction=ai_pred,
            warning=warn,
            provenance=prov,

            telemetry_timestamp=prov.get("telemetry_timestamp", res.get("timestamp", "")),
            feature_window_start=prov.get("feature_window_start"),
            feature_window_end=prov.get("feature_window_end"),
            prediction_timestamp=prov.get("prediction_timestamp", res.get("timestamp", "")),
            warning_timestamp=warn.get("warning_timestamp"),

            camera_health_status=cam_h.get("status", "ONLINE"),
            processing_mode=prov.get("processing_mode", "LIVE"),
            telemetry_source=prov.get("telemetry_source", "live_cctv_gps"),

            person_count=int(telem.get("person_count", 0)),
            tracked_person_count=int(telem.get("tracked_person_count", 0)),
            density=float(telem.get("density", 0.0)),
            average_speed=float(telem.get("average_speed", 1.2)),
            median_speed=float(telem.get("median_speed", 1.1)),
            inflow_rate=float(telem.get("inflow_rate", 0.0)),
            outflow_rate=float(telem.get("outflow_rate", 0.0)),
            flow_imbalance=float(telem.get("flow_imbalance", 0.0)),
            net_accumulation=float(telem.get("net_accumulation", 0.0)),
            direction_conflict_score=float(telem.get("direction_conflict_score", 0.0)),
            reverse_flow_ratio=float(telem.get("reverse_flow_ratio", 0.0)),
            blockage_score=float(telem.get("blockage_score", 0.0)),

            current_physics_risk=float(c_risk.get("score", c_risk.get("current_risk", 0.0))),
            current_risk_level=str(c_risk.get("bucket", c_risk.get("current_risk_level", "LOW"))),

            model_version=str(ai_pred.get("model_version", "v2.0.0")),
            target=str(ai_pred.get("target", "EARLY_ESCALATION_5M")),
            target_version="v1.0.0",
            horizon_seconds=int(ai_pred.get("horizon_seconds", 300)),
            ai_status=str(ai_pred.get("status", ai_pred.get("prediction_status", "SUCCESS"))),
            ai_probability=ai_pred.get("probability"),
            history_ready=bool(ai_pred.get("history_ready", False)),

            operational_warning_state=str(warn.get("operational_warning_state", "NORMAL")),
            warning_reason=warn.get("warning_reason"),
            persistence_count=int(warn.get("persistence_count", 0)),

            calibration_status=str(prov.get("calibration_status", "UNCALIBRATED")),
            confidence_score=float(prov.get("confidence_score", 1.0)),
            data_quality="LOW" if prov.get("is_degraded") else "HIGH",
            is_degraded=bool(prov.get("is_degraded", False)),

            model_status=str(prov.get("model_status", "PROTOTYPE")),
            label_type=str(prov.get("label_type", "PHYSICS_DEFINED_PROXY")),
            ground_truth_status=str(prov.get("ground_truth_status", "NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED")),
            generalization_status=str(prov.get("generalization_status", "INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION")),
            disclaimer=str(prov.get("disclaimer", "AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.")),
        )
