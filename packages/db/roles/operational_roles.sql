-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- DB Roles: Enforcing append-only execution log at the DB permission level
-- Implements: NFR-004, DDD §5
--
-- CRITICAL: These roles enforce the non-negotiable constraint that
-- ExecutionLog is append-only. No application code change can bypass this.
-- ============================================================================

-- === Application Role ===
-- General read/write for most operational tables, but NO UPDATE/DELETE on execution_log
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'chief_app') THEN
        CREATE ROLE chief_app LOGIN PASSWORD 'changeme_operational';
    END IF;
END $$;

GRANT CONNECT ON DATABASE chief_operational TO chief_app;
GRANT USAGE ON SCHEMA public TO chief_app;

-- Grant full CRUD on most tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO chief_app;

-- REVOKE write permissions on execution_log from the app role
-- NFR-004: "REVOKE UPDATE, DELETE at the DB role level"
REVOKE UPDATE, DELETE ON execution_log FROM chief_app;
REVOKE INSERT ON execution_log FROM chief_app;

-- === Execution Log Writer Role ===
-- Only this role can INSERT into execution_log. Used exclusively by the Execution Service.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'chief_execution_writer') THEN
        CREATE ROLE chief_execution_writer LOGIN PASSWORD 'changeme_exec_writer';
    END IF;
END $$;

GRANT CONNECT ON DATABASE chief_operational TO chief_execution_writer;
GRANT USAGE ON SCHEMA public TO chief_execution_writer;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chief_execution_writer;
GRANT INSERT ON execution_log TO chief_execution_writer;
-- Explicitly deny UPDATE and DELETE
REVOKE UPDATE, DELETE ON execution_log FROM chief_execution_writer;

-- === Audit Reader Role ===
-- Read-only access to execution_log and related tables for audit queries.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'chief_audit_reader') THEN
        CREATE ROLE chief_audit_reader LOGIN PASSWORD 'changeme_audit_reader';
    END IF;
END $$;

GRANT CONNECT ON DATABASE chief_operational TO chief_audit_reader;
GRANT USAGE ON SCHEMA public TO chief_audit_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chief_audit_reader;

-- Ensure no write access for audit reader
REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM chief_audit_reader;

-- === Grant sequence usage ===
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO chief_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO chief_execution_writer;

COMMENT ON ROLE chief_app IS 'General application role. Cannot modify execution_log (INSERT/UPDATE/DELETE revoked).';
COMMENT ON ROLE chief_execution_writer IS 'Execution Service role. Can INSERT into execution_log only. Cannot UPDATE/DELETE.';
COMMENT ON ROLE chief_audit_reader IS 'Audit/read-only role. SELECT only on all tables.';
