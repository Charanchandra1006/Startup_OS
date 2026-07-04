-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- Migration 001: Create Tenants Table
-- Implements: DDD §2 (Tenant entity), SGD §1 (data classification)
-- ============================================================================

CREATE TABLE IF NOT EXISTS tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    plan_tier       VARCHAR(50) NOT NULL DEFAULT 'design_partner',
    settings        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for lookups
CREATE INDEX idx_tenants_plan_tier ON tenants(plan_tier);

-- Enable Row Level Security
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

-- RLS Policy: app role can only see their own tenant
-- (tenant_id is set via session variable by the application layer)
CREATE POLICY tenant_isolation_policy ON tenants
    USING (id = current_setting('app.current_tenant_id', true)::UUID);

COMMENT ON TABLE tenants IS 'Multi-tenant company entities. DDD §2, SGD §1 Tier 3 (Operational).';
