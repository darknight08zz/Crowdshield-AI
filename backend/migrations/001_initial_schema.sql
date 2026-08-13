-- CrowdShield Migration 001: Initial Database Schema
-- Target Database: PostgreSQL (Supabase)

-- Enable UUID extension if not already active
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Create Enums
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('citizen', 'field_officer', 'operator', 'event_admin', 'system_admin');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE gate_type AS ENUM ('entry', 'exit', 'emergency', 'bidirectional');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE gate_status AS ENUM ('open', 'restricted', 'closed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE incident_status AS ENUM ('reported', 'verified', 'false_alarm', 'resolved');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE assignment_status AS ENUM ('assigned', 'acknowledged', 'in_progress', 'completed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE recommendation_status AS ENUM ('pending', 'approved', 'modified', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Create Tables

-- USERS TABLE
-- Stores profile and role mapping linked to Supabase Auth UUID or custom platform user ID
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role user_role NOT NULL DEFAULT 'citizen',
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- EVENTS TABLE
-- High-level public safety events managed by Control Room and Event Admins
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    date TIMESTAMPTZ NOT NULL,
    venue VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'upcoming', -- upcoming, active, completed, cancelled
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ZONES TABLE
-- Specific sub-areas within an event venue monitored for crowd density & risk
CREATE TABLE IF NOT EXISTS zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    capacity INT NOT NULL CHECK (capacity > 0),
    current_density FLOAT NOT NULL DEFAULT 0.0 CHECK (current_density >= 0.0),
    risk_score FLOAT NOT NULL DEFAULT 0.0 CHECK (risk_score >= 0.0 AND risk_score <= 1.0),
    geo_polygon JSONB, -- GeoJSON Polygon coordinates defining zone perimeter
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- GATES TABLE
-- Entry, exit, and emergency choke points associated with zones and events
CREATE TABLE IF NOT EXISTS gates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    zone_id UUID REFERENCES zones(id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    type gate_type NOT NULL DEFAULT 'entry',
    capacity_per_min INT NOT NULL DEFAULT 100 CHECK (capacity_per_min >= 0),
    status gate_status NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- INCIDENTS TABLE
-- Crowd safety incident reports filed by citizens or officers
CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id UUID REFERENCES users(id) ON DELETE SET NULL,
    zone_id UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- e.g. crowd_surge, medical, bottleneck, hazard
    description TEXT,
    media_url TEXT,
    status incident_status NOT NULL DEFAULT 'reported',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- OFFICER ASSIGNMENTS TABLE
-- Tasks dispatched from Control Room to Field Officers for incident response or crowd control
CREATE TABLE IF NOT EXISTS officer_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    officer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    zone_id UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    task_description TEXT NOT NULL,
    status assignment_status NOT NULL DEFAULT 'assigned',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- AI RECOMMENDATIONS TABLE
-- ML risk model scoring, 5-min predictions, and explainable intervention options
CREATE TABLE IF NOT EXISTS ai_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    risk_score FLOAT NOT NULL CHECK (risk_score >= 0.0 AND risk_score <= 1.0),
    predicted_risk_5min FLOAT NOT NULL CHECK (predicted_risk_5min >= 0.0 AND predicted_risk_5min <= 1.0),
    recommended_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    status recommendation_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- AUDIT LOG TABLE
-- Compliance and forensic log tracking all Operator/Admin actions and system decisions
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    target VARCHAR(100) NOT NULL,
    before_state JSONB,
    after_state JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Indexes for High-Frequency Realtime & Dashboard Queries
-- Foreign key indices ensure fast JOINs and filtered real-time query performance.

CREATE INDEX IF NOT EXISTS idx_zones_event_id ON zones(event_id);
CREATE INDEX IF NOT EXISTS idx_gates_event_id ON gates(event_id);
CREATE INDEX IF NOT EXISTS idx_gates_zone_id ON gates(zone_id);

CREATE INDEX IF NOT EXISTS idx_incidents_zone_id ON incidents(zone_id);
CREATE INDEX IF NOT EXISTS idx_incidents_reporter_id ON incidents(reporter_id);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);

CREATE INDEX IF NOT EXISTS idx_officer_assignments_zone_id ON officer_assignments(zone_id);
CREATE INDEX IF NOT EXISTS idx_officer_assignments_officer_id ON officer_assignments(officer_id);
CREATE INDEX IF NOT EXISTS idx_officer_assignments_status ON officer_assignments(status);

CREATE INDEX IF NOT EXISTS idx_ai_recommendations_zone_id ON ai_recommendations(zone_id);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_status ON ai_recommendations(status);

CREATE INDEX IF NOT EXISTS idx_audit_log_actor_id ON audit_log(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);

-- Enable Row Level Security (RLS) on all core tables for Supabase policy enforcement
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE zones ENABLE ROW LEVEL SECURITY;
ALTER TABLE gates ENABLE ROW LEVEL SECURITY;
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE officer_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
