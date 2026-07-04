-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- Migration 002: Create Users Table
-- Implements: DDD §2 (User entity)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email               VARCHAR(255) NOT NULL,
    name                VARCHAR(255),
    role                VARCHAR(50) NOT NULL DEFAULT 'founder',
    auth_provider_ref   VARCHAR(255),  -- Reference to external auth provider user ID
    is_active           BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_users_tenant_email UNIQUE (tenant_id, email)
);

CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_tenant_isolation ON users
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

COMMENT ON TABLE users IS 'Users within a tenant. DDD §2. Roles: founder, co_founder, admin, viewer.';
