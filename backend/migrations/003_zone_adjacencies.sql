-- Migration: 003_zone_adjacencies.sql
-- Create zone_adjacencies table for Panic Propagation modeling

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'connection_type_enum') THEN
        CREATE TYPE connection_type_enum AS ENUM ('gate', 'open_path', 'corridor');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS zone_adjacencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    zone_a_id UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    zone_b_id UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    connection_type connection_type_enum NOT NULL DEFAULT 'open_path',
    connection_capacity FLOAT NOT NULL DEFAULT 100.0,
    vector_direction VARCHAR(50) DEFAULT 'bidirectional',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_zone_adjacencies_event_id ON zone_adjacencies(event_id);
CREATE INDEX IF NOT EXISTS idx_zone_adjacencies_zone_a_id ON zone_adjacencies(zone_a_id);
CREATE INDEX IF NOT EXISTS idx_zone_adjacencies_zone_b_id ON zone_adjacencies(zone_b_id);
