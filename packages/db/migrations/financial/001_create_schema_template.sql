-- ============================================================================
-- Chief AI Startup OS — Financial/Legal Store
-- Migration 001: Tenant Schema Template
-- Implements: DDD §3 (schema-per-tenant), SGD §1 (Tier 1 Critical data)
--
-- Each tenant gets its own schema in this database.
-- This provides stronger isolation than row-level security alone.
-- A query bug in application code cannot cross tenant boundaries because
-- the database connection itself is scoped per tenant for this store.
-- ============================================================================

-- This is a TEMPLATE. When a new tenant is provisioned, this template is
-- applied with the tenant's UUID as the schema name.
-- Example: CREATE SCHEMA tenant_<uuid>;

-- The provisioning function:
CREATE OR REPLACE FUNCTION create_tenant_financial_schema(p_tenant_id UUID)
RETURNS void AS $$
DECLARE
    schema_name TEXT := 'tenant_' || replace(p_tenant_id::text, '-', '_');
BEGIN
    -- Create tenant-specific schema
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', schema_name);

    -- Create FinancialTransaction table in tenant schema
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.financial_transactions (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL DEFAULT %L,
            source_system       VARCHAR(100) NOT NULL,
            external_ref        VARCHAR(255),
            amount              DECIMAL(15,2) NOT NULL,
            currency            VARCHAR(3) NOT NULL DEFAULT ''USD'',
            category            VARCHAR(100),
            description         TEXT,
            transaction_date    DATE NOT NULL,
            ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            anomaly_flag        BOOLEAN NOT NULL DEFAULT false,
            anomaly_detail      JSONB,
            raw_data            JSONB,
            -- Per-tenant envelope encryption key reference
            -- The actual key lives in the credential vault
            encryption_key_ref  VARCHAR(255),
            CONSTRAINT chk_tenant_id CHECK (tenant_id = %L)
        )', schema_name, p_tenant_id, p_tenant_id);

    -- Create LegalDocument metadata table
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.legal_documents (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL DEFAULT %L,
            doc_type        VARCHAR(100) NOT NULL,
            title           VARCHAR(500),
            source_ref      VARCHAR(255),
            status          VARCHAR(50) NOT NULL DEFAULT ''active'',
            review_flags    JSONB DEFAULT ''[]'',
            encryption_key_ref VARCHAR(255),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_tenant_id CHECK (tenant_id = %L)
        )', schema_name, p_tenant_id, p_tenant_id);

    -- Create indexes
    EXECUTE format('
        CREATE INDEX IF NOT EXISTS idx_ft_date ON %I.financial_transactions(transaction_date DESC);
        CREATE INDEX IF NOT EXISTS idx_ft_category ON %I.financial_transactions(category);
        CREATE INDEX IF NOT EXISTS idx_ft_anomaly ON %I.financial_transactions(anomaly_flag) WHERE anomaly_flag = true;
        CREATE INDEX IF NOT EXISTS idx_ld_type ON %I.legal_documents(doc_type);
    ', schema_name, schema_name, schema_name, schema_name);

    -- Grant access to financial app role
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO chief_financial_app', schema_name);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA %I TO chief_financial_app', schema_name);

    -- Grant read-only to audit role
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO chief_financial_audit', schema_name);
    EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO chief_financial_audit', schema_name);

    RAISE NOTICE 'Created financial schema for tenant %', p_tenant_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION create_tenant_financial_schema IS
    'Creates schema-per-tenant isolation for financial/legal data. DDD §3, SGD §1. '
    'Each tenant gets a CHECK constraint on tenant_id as defense in depth.';
