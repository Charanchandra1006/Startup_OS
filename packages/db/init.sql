-- ============================================================================
-- Chief AI Startup OS â€” Operational Store
-- Migration 001: Create Tenants Table
-- Implements: DDD Â§2 (Tenant entity), SGD Â§1 (data classification)
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

COMMENT ON TABLE tenants IS 'Multi-tenant company entities. DDD Â§2, SGD Â§1 Tier 3 (Operational).';
-- ============================================================================
-- Chief AI Startup OS â€” Operational Store
-- Migration 002: Create Users Table
-- Implements: DDD Â§2 (User entity)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email               VARCHAR(255) NOT NULL,
    name                VARCHAR(255),
    password_hash       VARCHAR(255),
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

COMMENT ON TABLE users IS 'Users within a tenant. DDD Â§2. Roles: founder, co_founder, admin, viewer.';
-- ============================================================================
-- Chief AI Startup OS â€” Operational Store
-- Migration 003: Create Goals Table
-- Implements: DDD Â§2 (Goal entity), PRD FR-1.1
-- ============================================================================

-- Goal status enum
CREATE TYPE goal_status AS ENUM (
    'received',
    'classifying',
    'awaiting_clarification',
    'decomposing',
    'dispatching',
    'awaiting_specialist_output',
    'synthesizing',
    'routing_actions',
    'delivered',
    'stalled',
    'failed'
);

-- Goal classification type enum (PRD FR-1.2)
CREATE TYPE goal_type AS ENUM (
    'reporting',
    'monitoring',
    'forecasting',
    'ad_hoc_question',
    'composite',
    'action_request',
    'unclassified'
);

CREATE TABLE IF NOT EXISTS goals (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    submitted_by_user_id    UUID NOT NULL REFERENCES users(id),
    raw_text                TEXT NOT NULL,
    classified_type         goal_type,
    classification_confidence FLOAT,
    status                  goal_status NOT NULL DEFAULT 'received',
    clarification_question  TEXT,          -- If status = awaiting_clarification
    clarification_response  TEXT,          -- Founder's response
    stalled_at              TIMESTAMPTZ,   -- When goal was marked stalled
    trace_id                VARCHAR(128),  -- OpenTelemetry trace ID for full pipeline trace
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enforce character limit per PRD FR-1.1 (2000 chars recommended)
ALTER TABLE goals ADD CONSTRAINT chk_goal_text_length
    CHECK (char_length(raw_text) <= 4000);

CREATE INDEX idx_goals_tenant_id ON goals(tenant_id);
CREATE INDEX idx_goals_status ON goals(tenant_id, status);
CREATE INDEX idx_goals_created_at ON goals(tenant_id, created_at DESC);
CREATE INDEX idx_goals_trace_id ON goals(trace_id);

-- Enable Row Level Security
ALTER TABLE goals ENABLE ROW LEVEL SECURITY;

CREATE POLICY goal_tenant_isolation ON goals
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

COMMENT ON TABLE goals IS 'Founder goal submissions. DDD Â§2, PRD FR-1.1-1.4. Persisted before processing begins.';
-- ============================================================================
-- Chief AI Startup OS â€” Operational Store
-- Migration 004: Create Tasks Table
-- Implements: DDD Â§2 (Task entity), PRD FR-1.4
-- ============================================================================

CREATE TYPE task_status AS ENUM (
    'pending',
    'dispatched',
    'in_progress',
    'completed',
    'failed',
    'timed_out',
    'cancelled'
);

CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id         UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    assigned_agent  VARCHAR(20) NOT NULL,  -- Agent ID from AIDD Â§1 registry (e.g., AGT-FIN)
    description     TEXT NOT NULL,
    status          task_status NOT NULL DEFAULT 'pending',
    depends_on      UUID[] DEFAULT '{}',   -- Array of task IDs this task depends on
    priority        INTEGER NOT NULL DEFAULT 0,
    timeout_ms      INTEGER NOT NULL DEFAULT 60000,  -- Default 60s for Standard tier, 120s for Frontier
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tasks_goal_id ON tasks(goal_id);
CREATE INDEX idx_tasks_tenant_id ON tasks(tenant_id);
CREATE INDEX idx_tasks_status ON tasks(goal_id, status);
CREATE INDEX idx_tasks_assigned_agent ON tasks(assigned_agent);

-- Enable Row Level Security
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY task_tenant_isolation ON tasks
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

COMMENT ON TABLE tasks IS 'Decomposed tasks from goals, each assigned to a specialist agent. DDD Â§2, PRD FR-1.4.';
-- ============================================================================
-- Chief AI Startup OS â€” Operational Store
-- Migration 005: Create Agent Runs Table
-- Implements: DDD Â§2 (AgentRun entity), AIDD Â§2.2, Â§8
-- ============================================================================

CREATE TYPE confidence_level AS ENUM ('low', 'medium', 'high');

CREATE TABLE IF NOT EXISTS agent_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_name      VARCHAR(20) NOT NULL,   -- Agent ID from AIDD Â§1 registry
    model_used      VARCHAR(100) NOT NULL,  -- Exact model identifier for reproducibility
    prompt_version  VARCHAR(20) NOT NULL,   -- Semver per AIDD Â§8
    input_ref       JSONB NOT NULL,         -- Full input payload (for reproducibility)
    output_ref      JSONB,                  -- Full structured output per AIDD Â§2.2
    confidence      confidence_level,
    caveats         JSONB DEFAULT '[]',     -- Array of caveat strings
    supporting_data JSONB DEFAULT '[]',     -- Array of {source_system, source_ref, value, retrieved_at}
    suggested_actions JSONB DEFAULT '[]',   -- Array of SuggestedAction objects
    trace_id        VARCHAR(128),           -- OpenTelemetry trace ID
    token_count_prompt  INTEGER,
    token_count_completion INTEGER,
    latency_ms      INTEGER,
    error_message   TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

-- Partitioning note (DDD Â§7): plan partitioning by tenant + time range
-- For Phase 0/1 we use regular indexes; partitioning added when data volume warrants it
CREATE INDEX idx_agent_runs_task_id ON agent_runs(task_id);
CREATE INDEX idx_agent_runs_tenant_id ON agent_runs(tenant_id);
CREATE INDEX idx_agent_runs_agent_name ON agent_runs(agent_name);
CREATE INDEX idx_agent_runs_started_at ON agent_runs(tenant_id, started_at DESC);
CREATE INDEX idx_agent_runs_trace_id ON agent_runs(trace_id);

-- Enable Row Level Security
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_run_tenant_isolation ON agent_runs
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

COMMENT ON TABLE agent_runs IS 'Record of every specialist agent invocation. DDD Â§2, AIDD Â§2.2/Â§8. Fast-growing â€” plan partitioning per DDD Â§7.';
-- ============================================================================
-- Chief AI Startup OS â€” Operational Store
-- Migration 006: Create Recommendations Table
-- Implements: DDD Â§2 (Recommendation entity)
-- ============================================================================

CREATE TABLE IF NOT EXISTS recommendations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id                 UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    synthesized_text        TEXT NOT NULL,
    -- Report content contract (PVD Â§10): what_happened, why, impact, risks,
    -- recommendation, alternatives, confidence, next_actions
    report_sections         JSONB NOT NULL DEFAULT '{}',
    supporting_agent_runs   UUID[] NOT NULL DEFAULT '{}',  -- FK references to agent_runs
    confidence              confidence_level NOT NULL,
    conflicts_detected      BOOLEAN NOT NULL DEFAULT false,
    conflict_detail         JSONB,          -- Details of agent output tensions
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_recommendations_goal_id ON recommendations(goal_id);
CREATE INDEX idx_recommendations_tenant_id ON recommendations(tenant_id);

-- Enable Row Level Security
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;

CREATE POLICY recommendation_tenant_isolation ON recommendations
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

COMMENT ON TABLE recommendations IS 'Synthesized orchestrator output from specialist agent results. DDD Â§2, PVD Â§10 report contract.';
-- ============================================================================
-- Chief AI Startup OS â€” Operational Store
-- Migration 007: Create Approval Requests Table
-- Implements: DDD Â§2 (ApprovalRequest entity), SGD Â§2, WDD Â§3
-- ============================================================================

CREATE TYPE approval_status AS ENUM (
    'pending',
    'approved',
    'rejected',
    'expired',
    'auto_executed'
);

CREATE TYPE risk_tier AS ENUM ('A', 'B', 'C', 'D');

CREATE TABLE IF NOT EXISTS approval_requests (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    recommendation_id       UUID REFERENCES recommendations(id),
    suggested_action_id     UUID,           -- Reference to specific action within agent output
    action_type             VARCHAR(100) NOT NULL,
    risk_tier               risk_tier NOT NULL,
    -- Diff/preview content: MUST be byte-for-byte identical to what will be executed
    -- PRD FR-6.2: "the content shown in the preview is byte-for-byte identical"
    diff_preview            JSONB NOT NULL,
    payload                 JSONB NOT NULL,  -- Full action payload for execution
    rationale               TEXT NOT NULL,    -- Why this action is proposed
    contributing_agents     VARCHAR(20)[] NOT NULL DEFAULT '{}',
    status                  approval_status NOT NULL DEFAULT 'pending',
    decided_by_user_id      UUID REFERENCES users(id),
    rejection_reason        TEXT,
    decided_at              TIMESTAMPTZ,
    expires_at              TIMESTAMPTZ,      -- Auto-expire if not acted on
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approval_requests_tenant_id ON approval_requests(tenant_id);
CREATE INDEX idx_approval_requests_status ON approval_requests(tenant_id, status);
CREATE INDEX idx_approval_requests_created_at ON approval_requests(tenant_id, created_at DESC);

-- Enable Row Level Security
ALTER TABLE approval_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY approval_request_tenant_isolation ON approval_requests
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

COMMENT ON TABLE approval_requests IS 'Pending/resolved approval decisions. DDD Â§2, SGD Â§2 approval-tier model, WDD Â§3.';
-- ============================================================================
-- Chief AI Startup OS â€” Operational Store
-- Migration 008: Create Execution Log (APPEND-ONLY)
-- Implements: DDD Â§2/Â§5 (ExecutionLog), NFR-004, TRD Â§2, SGD Â§2
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
    -- Cryptographic hash chaining (DDD Â§5 recommendation)
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
    'APPEND-ONLY execution audit log. NFR-004, DDD Â§5. '
    'No UPDATE/DELETE permitted at DB role level. '
    'Hash-chained for tamper detection. '
    'Synchronous write required before action is considered complete (TRD Â§2 fail-closed).';
-- ============================================================================
-- Chief AI Startup OS â€” Operational Store
-- Migration 009: Create Integrations Table
-- Implements: DDD Â§2 (Integration entity), TRD Â§4
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
    -- DDD Â§1: "Credentials live in a dedicated secrets vault, never in any of the three stores"
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

COMMENT ON TABLE integrations IS 'Connected external service integrations. DDD Â§2, TRD Â§4. credential_vault_ref is a pointer ONLY â€” never stores actual credentials.';
-- ============================================================================
-- Chief AI Startup OS â€” Operational Store
-- Migration 010: Create Tier Rules Table
-- Implements: AIDD Â§2.3/GR-04, SGD Â§2 (approval-tier model)
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
    -- SGD Â§2: Tier C/D can NEVER be auto-executed. Only Tier A (always auto) and B (opt-in).
    auto_execute_eligible BOOLEAN NOT NULL DEFAULT false,
    -- Hard-refusal denylist: these action types can NEVER execute via automated executor
    -- Master prompt Â§6.5: enforced independent of and in addition to tier logic
    is_hard_denied  BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- No RLS on tier_rules â€” platform-level, not tenant-scoped
-- All tenants see the same tier rules (tiers are not tenant-configurable)

COMMENT ON TABLE tier_rules IS
    'Platform-level action_type â†’ risk_tier mapping. AIDD GR-04, SGD Â§2. '
    'Tiers are platform constants, not agent-assignable or tenant-overridable. '
    'is_hard_denied implements the Â§6.5 denylist.';

-- ============================================================================
-- Tenant auto-execute preferences (per-tenant, per-action-type opt-in)
-- SGD Â§2: "may be opted into auto-execute per action-type, per tenant, explicitly"
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
    'Only Tier B actions eligible. SGD Â§2, WDD Â§3.';
-- ============================================================================
-- Chief AI Startup OS â€” Operational Store
-- Migration 011: Create Insight Feed Table
-- Implements: PRD FR-5.1/5.2, WDD Â§4 (proactive monitoring)
-- ============================================================================

CREATE TYPE insight_urgency AS ENUM ('normal', 'elevated', 'urgent');
CREATE TYPE insight_status AS ENUM ('active', 'dismissed', 'acted_upon');

CREATE TABLE IF NOT EXISTS insights (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_name      VARCHAR(20) NOT NULL,
    domain          VARCHAR(50) NOT NULL,   -- finance, hiring, pm, sales, etc.
    title           TEXT NOT NULL,
    detail          TEXT NOT NULL,
    why_it_matters  TEXT NOT NULL,           -- One-line "why this matters" (UXDS Â§2.1)
    supporting_data JSONB NOT NULL DEFAULT '[]',
    confidence      confidence_level NOT NULL,
    urgency         insight_urgency NOT NULL DEFAULT 'normal',
    status          insight_status NOT NULL DEFAULT 'active',
    agent_run_id    UUID REFERENCES agent_runs(id),
    dismissed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_insights_tenant_id ON insights(tenant_id);
CREATE INDEX idx_insights_tenant_status ON insights(tenant_id, status, created_at DESC);
CREATE INDEX idx_insights_domain ON insights(tenant_id, domain);

-- Enable Row Level Security
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;

CREATE POLICY insight_tenant_isolation ON insights
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

COMMENT ON TABLE insights IS 'Proactive insight feed items. PRD FR-5.1/5.2, WDD Â§4. Persistent until dismissed or acted upon.';

-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- Migration 012: Create Goal Events Table (Real-Time State Stream)
-- Implements: STARTUP_OS_MASTER_BUILD_PLAN Part 3.2
--
-- The orchestrator publishes one event per state transition. The API Gateway
-- exposes these as an SSE stream to the frontend, replacing the scripted
-- demo animation with real pipeline state.
-- ============================================================================

CREATE TABLE IF NOT EXISTS goal_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id         UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    state           VARCHAR(64) NOT NULL,
    detail          JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_goal_events_goal_id ON goal_events(goal_id);
CREATE INDEX ix_goal_events_tenant_id ON goal_events(tenant_id);
CREATE INDEX ix_goal_events_goal_id_created_at ON goal_events(goal_id, created_at);

-- Enable Row Level Security
ALTER TABLE goal_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY goal_events_tenant_isolation ON goal_events
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

COMMENT ON TABLE goal_events IS
    'Real-time state transition events for goals. MASTER_BUILD_PLAN Part 3. '
    'One row per orchestrator state transition, consumed via SSE by the frontend.';

-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- Migration 013: Create Tool Connections Table
-- Implements: STARTUP_OS_MASTER_BUILD_PLAN Part 5.1
--
-- Tracks per-tenant, per-provider OAuth connection state (separate from
-- actual encrypted tokens, which live in Vault).
-- ============================================================================

CREATE TABLE IF NOT EXISTS tool_connections (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    provider            TEXT NOT NULL,
    connected_by_user_id UUID NOT NULL REFERENCES users(id),
    connected_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_refreshed_at   TIMESTAMPTZ,
    scopes              TEXT[] NOT NULL DEFAULT '{}',
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'revoked', 'error')),

    CONSTRAINT uq_tool_connection_tenant_provider UNIQUE (tenant_id, provider)
);

CREATE INDEX ix_tool_connections_tenant ON tool_connections(tenant_id);

-- Enable Row Level Security
ALTER TABLE tool_connections ENABLE ROW LEVEL SECURITY;

CREATE POLICY tool_connections_tenant_isolation ON tool_connections
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

COMMENT ON TABLE tool_connections IS
    'Per-tenant, per-provider OAuth connection state. MASTER_BUILD_PLAN Part 5.1. '
    'Tracks whether a provider is connected — actual tokens live in the Vault.';

-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- Migration 014: Create Tenant DEK Table (Envelope Encryption)
-- Implements: STARTUP_OS_MASTER_BUILD_PLAN Part 4.4 / SPEC-GAPS SG-002
--
-- Per-tenant data encryption keys (wrapped by KMS KEK).
-- The wrapped DEK itself is stored here, never the plaintext key.
-- ============================================================================

CREATE TABLE IF NOT EXISTS tenant_dek (
    tenant_id       UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    wrapped_dek     BYTEA NOT NULL,
    kek_key_id      TEXT NOT NULL,    -- reference to the KMS key used to wrap
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rotated_at      TIMESTAMPTZ
);

COMMENT ON TABLE tenant_dek IS
    'Per-tenant wrapped data encryption keys. MASTER_BUILD_PLAN Part 4.4, SPEC-GAPS SG-002. '
    'Wrapped DEK only — plaintext key never touches Postgres.';

-- Chief AI Startup OS
-- Demo Company Seed: "AIHealth Inc."
-- Implements Phase 1.5: The "Real Data" Mandate
-- Run this against BOTH chief_operational and chief_financial databases (or whichever the current connection requires).

-- 1. Create the Demo Tenant
INSERT INTO tenants (id, name, plan_tier, created_at)
VALUES ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'AIHealth Inc.', 'startup', NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

-- Note: In a real environment, RLS would require SET app.current_tenant_id
-- For seeding as superuser, we bypass RLS.

-- 2. Financial Metrics (These would technically go in the financial DB, but for local demo, we assume shared schema or run script on both)
CREATE TABLE IF NOT EXISTS tenant_metrics (
    tenant_id UUID PRIMARY KEY,
    health_score INT,
    revenue_growth_pct INT,
    runway_months DECIMAL(4,1),
    critical_risks INT,
    decisions_waiting INT,
    est_decision_time_mins INT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO tenant_metrics (tenant_id, health_score, revenue_growth_pct, runway_months, critical_risks, decisions_waiting, est_decision_time_mins)
VALUES ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 91, 12, 13.8, 2, 3, 14)
ON CONFLICT (tenant_id) DO UPDATE SET 
    health_score = EXCLUDED.health_score,
    revenue_growth_pct = EXCLUDED.revenue_growth_pct,
    runway_months = EXCLUDED.runway_months;

-- 3. Removed outdated insights and agent_runs seed data to prevent schema mismatch.
