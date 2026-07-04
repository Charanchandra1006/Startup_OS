-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- Migration 009: Create Integrations Table
-- Implements: DDD §2 (Integration entity), TRD §4
-- ============================================================================

CREATE TYPE integration_category AS ENUM (
    'accounting',
    'ats',
    'crm',
    'pm',
    'calendar',
    'email',
    'docs',
    'analytics',
    'ci_cd',
    'support'
);

CREATE TYPE integration_status AS ENUM (
    'active',
    'inactive',
    'error',
    'pending_setup',
    'revoked'
);

CREATE TABLE IF NOT EXISTS integrations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    provider            VARCHAR(100) NOT NULL,     -- e.g., 'quickbooks', 'greenhouse', 'linear'
    category            integration_category NOT NULL,
    scope_granted       JSONB NOT NULL DEFAULT '[]',  -- Array of scopes granted
    -- CRITICAL: Only a pointer to the credential vault, never the credential itself
    -- DDD §1: "Credentials live in a dedicated secrets vault, never in any of the three stores"
    credential_vault_ref VARCHAR(255),
    status              integration_status NOT NULL DEFAULT 'pending_setup',
    last_sync_at        TIMESTAMPTZ,
    last_error          TEXT,
    config              JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_integration_tenant_provider UNIQUE (tenant_id, provider)
);

CREATE INDEX idx_integrations_tenant_id ON integrations(tenant_id);
CREATE INDEX idx_integrations_category ON integrations(tenant_id, category);

-- Enable Row Level Security
ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY integration_tenant_isolation ON integrations
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

COMMENT ON TABLE integrations IS 'Connected external service integrations. DDD §2, TRD §4. credential_vault_ref is a pointer ONLY — never stores actual credentials.';
