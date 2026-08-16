# CrowdShield — Phase 6D.1 Incident Data Model & Lifecycle Foundation

## Executive Summary

Phase 6D.1 establishes the canonical backend foundation for operational incident management within CrowdShield. It bridges real-time computer vision and temporal AI warnings (Phases 6A–6C.4) with human operator decision-making and emergency workflow tracking.

### Key Architectural Boundaries
1. **AI Warning vs. Operational Incident**: Not all telemetry warnings constitute persistent incidents. Warnings indicate situational risk; Incidents represent trackable operational workflows requiring human verification, investigation, or mitigation.
2. **Human-In-The-Loop**: Telemetry recovery (e.g. `HIGH_RISK` -> `NORMAL`) updates an incident's latest context but **never auto-resolves** an active incident. Operational incidents must be explicitly evaluated and resolved by human operators.
3. **Auditability & Provenance**: Every state transition appends an immutable transition log (`IncidentTransition`) detailing actor type (`SYSTEM` vs. `OPERATOR`), actor ID, timestamp, and justification notes, while preserving initial AI provenance disclaimers.
4. **Configurable Incident Policy**: Automatic incident triggering on `EARLY_WARNING` or `HIGH_RISK` is an operational policy configuration (`INCIDENT_POLICY_TRIGGER_STATES` in `backend/app/core/config.py`) rather than a scientifically validated AI model ground truth. The policy threshold can be dynamically configured per deployment without altering underlying CV/AI models.

---

## Architecture Diagram

```text
 CCTV / CV Pipeline (6A)
          │
          ▼
 Real-Time Telemetry Stream (6B)
          │
          ▼
 Incident Creation Policy Engine
   ├── Warning == NORMAL / WATCH ──> Ignore
   └── Warning == EARLY_WARNING / HIGH_RISK
          │
          ├── Active Incident Exists for (event, camera, zone) ──> Update Latest Context (Deduplicated)
          └── No Active Incident ──> Create Canonical Incident (OPEN) + Initial SYSTEM Audit Log
                                             │
                                             ▼
                                  Operator Decision Engine
                                             │
                          ┌──────────────────┴──────────────────┐
                          ▼                                     ▼
                    ACKNOWLEDGED                          FALSE_POSITIVE (Terminal)
                          │
                          ▼
                    INVESTIGATING
                          │
                          ▼
                     MITIGATING
                          │
                          ▼
                      RESOLVED (Terminal)
```

---

## Incident Data Model Schema

### `Incident` (SQLAlchemy: `incidents`)
| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `incident_id` | String(64) | Unique human-readable ID (`INC-YYYYMMDD-XXXX`) |
| `event_id` | String(64) | Associated event identifier |
| `camera_id` | String(64) | Associated camera ID (nullable for zone-wide incidents) |
| `zone_id` | String(64) | Associated zone identifier |
| `status` | String(32) | Deterministic state machine status |
| `source_type` | String(64) | Inception trigger source (`AI_EARLY_WARNING_PROXY`) |
| `warning_state_at_creation` | String(32) | Snapshot warning state at incident creation |
| `physics_risk_at_creation` | Float | Snapshot physics risk score at creation |
| `ai_probability_at_creation` | Float | Snapshot AI escalation probability at creation |
| `telemetry_timestamp` | String(64) | Initial telemetry frame timestamp |
| `prediction_timestamp` | String(64) | Initial AI prediction timestamp |
| `latest_warning_state` | String(32) | Dynamic updated warning state |
| `latest_physics_risk` | Float | Dynamic updated physics risk |
| `latest_ai_probability` | Float | Dynamic updated AI probability |
| `latest_telemetry_timestamp` | String(64) | Dynamic updated telemetry frame timestamp |
| `camera_health_status` | String(32) | Camera health state at operational time (`ONLINE`, `DEGRADED`) |
| `is_stale` | Boolean | Telemetry staleness flag |
| `is_degraded` | Boolean | Telemetry degraded flag |
| `model_version` | String(32) | Provenance: Model version string (`v2.0.0`) |
| `prediction_target` | String(64) | Provenance: Prediction target (`EARLY_ESCALATION_5M`) |
| `label_type` | String(64) | Provenance: Ground truth label type (`PHYSICS_DEFINED_PROXY`) |
| `model_status` | String(32) | Provenance: Model operational readiness (`PROTOTYPE`) |
| `ground_truth_status` | String(128)| Provenance disclaimer |
| `generalization_status` | String(128)| Provenance disclaimer |
| `disclaimer` | Text | Mandatory prototype warning disclaimer |
| `acknowledged_by` | String(128)| User ID of operator acknowledging incident |
| `acknowledged_at` | DateTime | Timestamp when incident was acknowledged |
| `resolved_by` | String(128)| User ID of operator resolving incident |
| `resolved_at` | DateTime | Timestamp when incident was resolved |
| `resolution_type` | String(64) | Resolution classification (`RESOLVED`, `FALSE_POSITIVE`) |
| `resolution_notes` | Text | Mandatory/optional operator resolution rationale |
| `created_at` | DateTime | Record creation timestamp |
| `updated_at` | DateTime | Last context update timestamp |

### `IncidentTransition` (SQLAlchemy: `incident_transitions`)
| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `transition_id` | String(64) | Unique transition ID (`TR-XXXXXX`) |
| `incident_id` | String(64) | Foreign key to `incidents.incident_id` |
| `previous_status` | String(32) | Status prior to transition |
| `new_status` | String(32) | Status after transition |
| `timestamp` | DateTime | Audit timestamp |
| `actor_type` | String(32) | `SYSTEM` (automated creation) or `OPERATOR` (manual action) |
| `actor_id` | String(128)| User ID of acting operator (or NULL for system) |
| `reason` | Text | Operator rationale or system trigger message |
| `metadata_json` | JSON/JSONB | Snapshot metadata captured at transition time |

---

## State Machine Transition Rules

| Initial State | Target State | Allowed? | Actor | Notes |
|---|---|---|---|---|
| `NONE` | `OPEN` | ✅ | SYSTEM | Automated creation trigger |
| `OPEN` | `ACKNOWLEDGED` | ✅ | OPERATOR | Operator confirms situational awareness |
| `OPEN` | `FALSE_POSITIVE` | ✅ | OPERATOR | Terminal branch for false alarms |
| `OPEN` | `INVESTIGATING` | ❌ | - | Invalid transition (must acknowledge first) |
| `ACKNOWLEDGED` | `INVESTIGATING` | ✅ | OPERATOR | Active investigation initiated |
| `ACKNOWLEDGED` | `FALSE_POSITIVE` | ✅ | OPERATOR | Terminal branch for false alarms |
| `ACKNOWLEDGED` | `RESOLVED` | ✅ | OPERATOR | Terminal branch for direct resolution |
| `INVESTIGATING` | `MITIGATING` | ✅ | OPERATOR | Active crowd mitigation actions deployed |
| `INVESTIGATING` | `RESOLVED` | ✅ | OPERATOR | Direct resolution post-investigation |
| `MITIGATING` | `RESOLVED` | ✅ | OPERATOR | Final resolution post-mitigation |
| `RESOLVED` | *Any* | ❌ | - | Terminal state (Locked) |
| `FALSE_POSITIVE` | *Any* | ❌ | - | Terminal state (Locked) |

---

## API Endpoint Specification

### 1. `GET /api/v1/operator/incidents`
- **Roles**: `operator`, `event_admin`, `system_admin`, `field_officer`
- **Query Filters**: `event_id`, `zone_id`, `camera_id`, `status`
- **Response**: List of `IncidentCanonicalResponse` objects.

### 2. `GET /api/v1/operator/incidents/{incident_id}`
- **Roles**: `operator`, `event_admin`, `system_admin`, `field_officer`
- **Response**: Detailed `IncidentCanonicalResponse` object including the complete `transitions` audit history array.

### 3. `POST /api/v1/operator/incidents/{incident_id}/transition`
- **Roles**: `operator`, `event_admin`, `system_admin`
- **Request Body**:
  ```json
  {
    "new_status": "ACKNOWLEDGED",
    "reason": "Operator checked CCTV feed and verified congestion."
  }
  ```
- **Behavior**:
  - Validates state transition rule against state machine matrix.
  - Extracts `actor_id` from authenticated JWT payload.
  - Appends new `IncidentTransition` record with `actor_type="OPERATOR"`.
  - Updates timestamps and operator tracking fields.

---

## Verification & Test Suite

The implementation is validated by a 13-scenario automated test suite located at `backend/tests/test_phase6d1_incident_model_contracts.py`.

```powershell
$env:PYTHONPATH="backend"; backend\venv\Scripts\pytest.exe backend/tests/test_phase6d1_incident_model_contracts.py -v
```

All 85 total backend tests across Phase 6 pass cleanly with zero regressions.
