-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- Migration 008: Create Execution Log (APPEND-ONLY)
-- Implements: DDD §2/§5 (ExecutionLog), NFR-004, TRD §2, SGD §2
--
-- CRITICAL NON-NEGOTIABLE:
-- This table is APPEND-ONLY. No UPDATE or DELETE is ever permitted.
-- Enforced at the database permission level, not just application logic.
-- This is the evidentiary backbone of the trust model.
-- ============================================================================

CREATE TABLE IF NOT EXISTS execution_log (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    approval_request_id     UUID NOT NULL REFERENCES approval_requests(id),
    action_type             VARCHAR(100) NOT NULL,
    target_system           VARCHAR(100) NOT NULL,
    -- Hash of the exact payload that was executed, for tamper detection
    payload_hash            VARCHAR(128) NOT NULL,
    -- The actual payload (for full traceability)
    payload_snapshot         JSONB NOT NULL,
    executed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    result_status           VARCHAR(50) NOT NULL,  -- success, failed, partial
    result_detail           JSONB,
    rollback_ref            VARCHAR(255),          -- If applicable
    -- Cryptographic hash chaining (DDD §5 recommendation)
    -- Each entry includes a hash of the previous entry for tamper detection
    previous_entry_hash     VARCHAR(128),
    entry_hash              VARCHAR(128) NOT NULL,
    -- Trace linkage
    trace_id                VARCHAR(128),
    -- Denormalized for audit queries without joins
    executed_by_user_id     UUID NOT NULL,
    risk_tier               risk_tier NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for audit queries
CREATE INDEX idx_execution_log_tenant_id ON execution_log(tenant_id);
CREATE INDEX idx_execution_log_tenant_time ON execution_log(tenant_id, created_at DESC);
CREATE INDEX idx_execution_log_action_type ON execution_log(action_type);
CREATE INDEX idx_execution_log_trace_id ON execution_log(trace_id);
CREATE INDEX idx_execution_log_approval ON execution_log(approval_request_id);

-- Enable Row Level Security
ALTER TABLE execution_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY execution_log_tenant_isolation ON execution_log
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

-- ============================================================================
-- CRITICAL: Append-only enforcement at the DB role level
-- The application role 'chief_app' is DENIED UPDATE and DELETE on this table.
-- Only the 'execution_log_writer' role can INSERT.
-- The 'chief_audit_reader' role can only SELECT.
-- This is enforced HERE, not in application code.
-- ============================================================================

-- These REVOKE/GRANT statements are applied in the roles migration (010)
-- but documented here as the table's design intent.

COMMENT ON TABLE execution_log IS
    'APPEND-ONLY execution audit log. NFR-004, DDD §5. '
    'No UPDATE/DELETE permitted at DB role level. '
    'Hash-chained for tamper detection. '
    'Synchronous write required before action is considered complete (TRD §2 fail-closed).';
