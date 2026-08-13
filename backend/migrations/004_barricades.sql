-- Migration: 004_barricades.sql
-- Description: Create barricades table for internal zone crowd flow shaping (Addendum Prompt 2)

CREATE TYPE barricade_config AS ENUM (
  'open',
  'narrow',
  'closed',
  'redirect_left',
  'redirect_right'
);

CREATE TABLE IF NOT EXISTS barricades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  zone_id UUID REFERENCES zones(id) ON DELETE SET NULL,
  name VARCHAR(100) NOT NULL,
  position_geometry JSONB,
  current_configuration barricade_config NOT NULL DEFAULT 'open',
  moveable BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_barricades_event ON barricades(event_id);
CREATE INDEX IF NOT EXISTS idx_barricades_zone ON barricades(zone_id);
