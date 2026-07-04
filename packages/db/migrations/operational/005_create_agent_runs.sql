-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- Migration 005: Create Agent Runs Table
-- Implements: DDD §2 (AgentRun entity), AIDD §2.2, §8
-- ============================================================================

CREATE TYPE confidence_level AS ENUM ('low', 'medium', 'high');

CREATE TABLE IF NOT EXISTS agent_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_name      VARCHAR(20) NOT NULL,   -- Agent ID from AIDD §1 registry
    model_used      VARCHAR(100) NOT NULL,  -- Exact model identifier for reproducibility
    prompt_version  VARCHAR(20) NOT NULL,   -- Semver per AIDD §8
    input_ref       JSONB NOT NULL,         -- Full input payload (for reproducibility)
    output_ref      JSONB,                  -- Full structured output per AIDD §2.2
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

-- Partitioning note (DDD §7): plan partitioning by tenant + time range
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

COMMENT ON TABLE agent_runs IS 'Record of every specialist agent invocation. DDD §2, AIDD §2.2/§8. Fast-growing — plan partitioning per DDD §7.';
