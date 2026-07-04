-- ============================================================================
-- Chief AI Startup OS — Financial/Legal Store
-- DB Roles: Separate credential/role from Operational Store
-- Implements: DDD §3, SGD §1 (Tier 1 — Critical data)
--
-- CRITICAL: Access to this store requires a DISTINCT credential/role
-- from the Operational Store. A compromised general application service
-- must not have implicit access to financial transaction detail.
-- ============================================================================

-- === Financial App Role ===
-- Used by the Finance Agent and Execution Service only
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'chief_financial_app') THEN
        CREATE ROLE chief_financial_app LOGIN PASSWORD 'changeme_financial';
    END IF;
END $$;

GRANT CONNECT ON DATABASE chief_financial TO chief_financial_app;

-- Note: actual schema grants are per-tenant schema, applied when tenant is provisioned
-- This role gets USAGE + CRUD on specific tenant schemas only

-- === Financial Audit Role ===
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'chief_financial_audit') THEN
        CREATE ROLE chief_financial_audit LOGIN PASSWORD 'changeme_financial_audit';
    END IF;
END $$;

GRANT CONNECT ON DATABASE chief_financial TO chief_financial_audit;
-- SELECT only, per-tenant schema, applied at tenant provisioning

COMMENT ON ROLE chief_financial_app IS 'Financial/Legal Store app role. DISTINCT from chief_app. DDD §3 isolation.';
COMMENT ON ROLE chief_financial_audit IS 'Financial/Legal Store audit reader. SELECT only.';
