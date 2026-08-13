-- CrowdShield Migration 002: Alerts & Push Device Tokens
-- Enables alert records and device FCM push registration

-- 1. Create Severity Enum
CREATE TYPE alert_severity AS ENUM ('low', 'medium', 'high', 'critical');

-- 2. Create Alerts Table
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    severity alert_severity NOT NULL DEFAULT 'medium',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Create Device Tokens Table
CREATE TABLE IF NOT EXISTS device_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fcm_token TEXT NOT NULL UNIQUE,
    platform VARCHAR(20) NOT NULL DEFAULT 'android',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Indexes for high-frequency notification queries
CREATE INDEX IF NOT EXISTS idx_alerts_zone_id ON alerts(zone_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_device_tokens_user_id ON device_tokens(user_id);

-- 5. Row Level Security Policies
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read access to alerts for authenticated users"
    ON alerts FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow users to manage their own device tokens"
    ON device_tokens FOR ALL
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
