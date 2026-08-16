-- Migration 006: Phase 6D.1 Canonical Incident Model and Transition Audit Log

-- 1. Extend canonical incidents table fields
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS incident_id VARCHAR(64);
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS event_id VARCHAR(64) DEFAULT 'evt_01';
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS camera_id VARCHAR(64);
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS source_type VARCHAR(64) DEFAULT 'AI_EARLY_WARNING_PROXY';
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS warning_state_at_creation VARCHAR(32) DEFAULT 'EARLY_WARNING';
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS physics_risk_at_creation DOUBLE PRECISION;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS ai_probability_at_creation DOUBLE PRECISION;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS telemetry_timestamp VARCHAR(64);
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS prediction_timestamp VARCHAR(64);
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS latest_warning_state VARCHAR(32);
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS latest_physics_risk DOUBLE PRECISION;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS latest_ai_probability DOUBLE PRECISION;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS latest_telemetry_timestamp VARCHAR(64);
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS camera_health_status VARCHAR(32) DEFAULT 'ONLINE';
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS is_stale BOOLEAN DEFAULT FALSE;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS is_degraded BOOLEAN DEFAULT FALSE;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS model_version VARCHAR(32) DEFAULT 'v2.0.0';
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS prediction_target VARCHAR(64) DEFAULT 'EARLY_ESCALATION_5M';
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS label_type VARCHAR(64) DEFAULT 'PHYSICS_DEFINED_PROXY';
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS model_status VARCHAR(32) DEFAULT 'PROTOTYPE';
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS ground_truth_status VARCHAR(128) DEFAULT 'NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED';
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS generalization_status VARCHAR(128) DEFAULT 'INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION';
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS disclaimer TEXT DEFAULT 'AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.';
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS acknowledged_by VARCHAR(128);
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS resolved_by VARCHAR(128);
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS resolution_type VARCHAR(64);
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS resolution_notes TEXT;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

CREATE UNIQUE INDEX IF NOT EXISTS idx_incidents_incident_id ON incidents(incident_id);
CREATE INDEX IF NOT EXISTS idx_incidents_event_id ON incidents(event_id);
CREATE INDEX IF NOT EXISTS idx_incidents_zone_id ON incidents(zone_id);
CREATE INDEX IF NOT EXISTS idx_incidents_camera_id ON incidents(camera_id);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);

-- 2. Create incident_transitions table for immutable transition audit log
CREATE TABLE IF NOT EXISTS incident_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transition_id VARCHAR(64) NOT NULL UNIQUE,
    incident_id VARCHAR(64) NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    previous_status VARCHAR(32) NOT NULL,
    new_status VARCHAR(32) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actor_type VARCHAR(32) NOT NULL,
    actor_id VARCHAR(128),
    reason TEXT,
    metadata_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_incident_transitions_incident ON incident_transitions(incident_id);
CREATE INDEX IF NOT EXISTS idx_incident_transitions_time ON incident_transitions(timestamp);
