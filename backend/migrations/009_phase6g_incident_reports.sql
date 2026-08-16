-- Migration 009: Phase 6G/6H Security Scope & Incident Reporting Hardening

CREATE TABLE IF NOT EXISTS incident_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id VARCHAR(64) UNIQUE NOT NULL,
    event_id VARCHAR(64) NOT NULL DEFAULT 'evt_01',
    zone_id VARCHAR(64),
    camera_id VARCHAR(64),
    submitted_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'REPORT_SUBMITTED',
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    reported_location VARCHAR(255),
    report_source VARCHAR(64) NOT NULL DEFAULT 'VIEWER',
    media_url TEXT,
    reviewed_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_reason TEXT,
    accepted_incident_id UUID REFERENCES incidents(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Performance and Query Indexes
CREATE INDEX IF NOT EXISTS idx_incident_reports_submitted_by ON incident_reports(submitted_by_user_id);
CREATE INDEX IF NOT EXISTS idx_incident_reports_status ON incident_reports(status);
CREATE INDEX IF NOT EXISTS idx_incident_reports_event_id ON incident_reports(event_id);
CREATE INDEX IF NOT EXISTS idx_incident_reports_created_at ON incident_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incident_reports_accepted_inc ON incident_reports(accepted_incident_id);
