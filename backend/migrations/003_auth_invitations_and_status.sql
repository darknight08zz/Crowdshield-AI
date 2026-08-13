-- CrowdShield Migration 003: Auth Account Status & User Invitations
-- Adds account status and invitation schema for RBAC staff provisioning

-- 1. Create Account Status Enum
DO $$ BEGIN
    CREATE TYPE account_status AS ENUM ('active', 'disabled', 'pending_verification', 'pending_invite');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Add columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS account_status VARCHAR(50) NOT NULL DEFAULT 'active';
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_otp VARCHAR(50);

-- 3. Create user_invitations table
CREATE TABLE IF NOT EXISTS user_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    invite_token VARCHAR(255) UNIQUE NOT NULL,
    invited_by UUID REFERENCES users(id) ON DELETE SET NULL,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Create indexes
CREATE INDEX IF NOT EXISTS idx_invitations_email ON user_invitations(email);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON user_invitations(invite_token);
CREATE INDEX IF NOT EXISTS idx_users_account_status ON users(account_status);

-- 5. Revoked Tokens Table for Server-Side Logout Revocation
CREATE TABLE IF NOT EXISTS revoked_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jti VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_revoked_tokens_jti ON revoked_tokens(jti);
