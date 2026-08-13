-- Migration 005: Create zone_metrics_history table for time-series analytics
CREATE TABLE IF NOT EXISTS zone_metrics_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    zone_id UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    density DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    inflow_rate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    outflow_rate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    avg_speed DOUBLE PRECISION NOT NULL DEFAULT 1.2,
    risk_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    behavior_classification VARCHAR(64) DEFAULT 'NORMAL',
    propagated_risk_score DOUBLE PRECISION DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_zone_metrics_zone_time ON zone_metrics_history (zone_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_zone_metrics_event_time ON zone_metrics_history (event_id, timestamp);
