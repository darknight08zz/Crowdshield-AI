-- Migration 007: Phase 6D.3 Response Officers, Dispatch Assignments, and Dispatch Audit Log

-- 1. Create response_officers table
CREATE TABLE IF NOT EXISTS response_officers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    officer_id VARCHAR(64) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(64) NOT NULL DEFAULT 'FIELD_OFFICER',
    status VARCHAR(32) NOT NULL DEFAULT 'AVAILABLE', -- AVAILABLE, ASSIGNED, BUSY, OFFLINE
    current_latitude DOUBLE PRECISION,
    current_longitude DOUBLE PRECISION,
    location_status VARCHAR(32) NOT NULL DEFAULT 'LOCATION_UNKNOWN', -- LOCATION_CURRENT, LOCATION_STALE, LOCATION_UNKNOWN
    location_timestamp TIMESTAMP WITH TIME ZONE,
    assigned_event_id VARCHAR(64) NOT NULL DEFAULT 'evt_01',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_response_officers_officer_id ON response_officers(officer_id);
CREATE INDEX IF NOT EXISTS idx_response_officers_status ON response_officers(status);
CREATE INDEX IF NOT EXISTS idx_response_officers_assigned_event ON response_officers(assigned_event_id);

-- 2. Create dispatch_assignments table
CREATE TABLE IF NOT EXISTS dispatch_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dispatch_id VARCHAR(64) UNIQUE NOT NULL,
    incident_id VARCHAR(64) NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    event_id VARCHAR(64) NOT NULL DEFAULT 'evt_01',
    officer_id VARCHAR(64) NOT NULL REFERENCES response_officers(officer_id) ON DELETE RESTRICT,
    status VARCHAR(32) NOT NULL DEFAULT 'ASSIGNED', -- UNASSIGNED, ASSIGNED, ACKNOWLEDGED, EN_ROUTE, ON_SCENE, RESPONDING, COMPLETED, CANCELLED
    assigned_by VARCHAR(128) NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    en_route_at TIMESTAMP WITH TIME ZONE,
    on_scene_at TIMESTAMP WITH TIME ZONE,
    responding_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    eta_minutes INTEGER DEFAULT 5,
    dispatch_reason TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dispatch_assignments_dispatch_id ON dispatch_assignments(dispatch_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_assignments_incident_id ON dispatch_assignments(incident_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_assignments_officer_id ON dispatch_assignments(officer_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_assignments_status ON dispatch_assignments(status);

-- 3. Create dispatch_transitions table for immutable transition audit log
CREATE TABLE IF NOT EXISTS dispatch_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transition_id VARCHAR(64) UNIQUE NOT NULL,
    dispatch_id VARCHAR(64) NOT NULL REFERENCES dispatch_assignments(dispatch_id) ON DELETE CASCADE,
    previous_status VARCHAR(32) NOT NULL,
    new_status VARCHAR(32) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actor_type VARCHAR(32) NOT NULL, -- SYSTEM, OPERATOR, FIELD_OFFICER
    actor_id VARCHAR(128),
    reason TEXT,
    metadata_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_dispatch_transitions_dispatch_id ON dispatch_transitions(dispatch_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_transitions_timestamp ON dispatch_transitions(timestamp);
