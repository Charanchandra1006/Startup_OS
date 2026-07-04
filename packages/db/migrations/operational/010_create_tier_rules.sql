-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- Migration 010: Create Tier Rules Table
-- Implements: AIDD §2.3/GR-04, SGD §2 (approval-tier model)
--
-- DESIGN RULE: Risk tiers are properties of action_types, set by the platform.
-- They are DATA ROWS, not if/else in agent code.
-- An agent cannot self-declare a lower tier to bypass friction.
-- ============================================================================

CREATE TABLE IF NOT EXISTS tier_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type     VARCHAR(100) NOT NULL UNIQUE,
    risk_tier       risk_tier NOT NULL,
    description     TEXT NOT NULL,
    -- Whether tenants can opt into auto-execute for this action type
    -- SGD §2: Tier C/D can NEVER be auto-executed. Only Tier A (always auto) and B (opt-in).
    auto_execute_eligible BOOLEAN NOT NULL DEFAULT false,
    -- Hard-refusal denylist: these action types can NEVER execute via automated executor
    -- Master prompt §6.5: enforced independent of and in addition to tier logic
    is_hard_denied  BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- No RLS on tier_rules — platform-level, not tenant-scoped
-- All tenants see the same tier rules (tiers are not tenant-configurable)

COMMENT ON TABLE tier_rules IS
    'Platform-level action_type → risk_tier mapping. AIDD GR-04, SGD §2. '
    'Tiers are platform constants, not agent-assignable or tenant-overridable. '
    'is_hard_denied implements the §6.5 denylist.';

-- ============================================================================
-- Tenant auto-execute preferences (per-tenant, per-action-type opt-in)
-- SGD §2: "may be opted into auto-execute per action-type, per tenant, explicitly"
-- Only Tier B actions are eligible. Tier A is always auto. Tier C/D never auto.
-- ============================================================================

CREATE TABLE IF NOT EXISTS tenant_auto_execute_preferences (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    action_type     VARCHAR(100) NOT NULL REFERENCES tier_rules(action_type),
    enabled         BOOLEAN NOT NULL DEFAULT false,
    enabled_by_user_id UUID REFERENCES users(id),
    enabled_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_tenant_auto_execute UNIQUE (tenant_id, action_type)
);

CREATE INDEX idx_tenant_auto_exec_tenant ON tenant_auto_execute_preferences(tenant_id);

-- Enable Row Level Security
ALTER TABLE tenant_auto_execute_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY auto_exec_tenant_isolation ON tenant_auto_execute_preferences
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

COMMENT ON TABLE tenant_auto_execute_preferences IS
    'Per-tenant opt-in for auto-execution of specific action types. '
    'Only Tier B actions eligible. SGD §2, WDD §3.';
