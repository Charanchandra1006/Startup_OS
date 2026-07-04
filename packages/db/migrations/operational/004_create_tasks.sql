-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- Migration 004: Create Tasks Table
-- Implements: DDD §2 (Task entity), PRD FR-1.4
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
    assigned_agent  VARCHAR(20) NOT NULL,  -- Agent ID from AIDD §1 registry (e.g., AGT-FIN)
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

COMMENT ON TABLE tasks IS 'Decomposed tasks from goals, each assigned to a specialist agent. DDD §2, PRD FR-1.4.';
