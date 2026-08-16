-- Migration 008: Phase 6G Security, RBAC & Immutable Audit Log Hardening

-- Upgrade existing audit_log table or create comprehensive audit_log table
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_role VARCHAR(50),
    action VARCHAR(100) NOT NULL,
    target VARCHAR(255) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    event_id VARCHAR(100),
    camera_id VARCHAR(100),
    zone_id VARCHAR(100),
    before_state JSONB,
    after_state JSONB,
    reason TEXT,
    success BOOLEAN DEFAULT TRUE,
    failure_code VARCHAR(50),
    request_id VARCHAR(100),
    source VARCHAR(100) DEFAULT 'API',
    metadata_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Add missing columns if audit_log table already existed in earlier migrations
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS actor_role VARCHAR(50);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS resource_type VARCHAR(50);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS resource_id VARCHAR(255);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS event_id VARCHAR(100);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS camera_id VARCHAR(100);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS zone_id VARCHAR(100);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS reason TEXT;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS success BOOLEAN DEFAULT TRUE;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS failure_code VARCHAR(50);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS request_id VARCHAR(100);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS source VARCHAR(100) DEFAULT 'API';
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS metadata_json JSONB;

-- Performance and Audit Search Indexes
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_actor_id ON audit_log(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_event_id ON audit_log(event_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_request_id ON audit_log(request_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_success ON audit_log(success);
