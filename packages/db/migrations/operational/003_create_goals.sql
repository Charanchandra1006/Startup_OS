-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- Migration 003: Create Goals Table
-- Implements: DDD §2 (Goal entity), PRD FR-1.1
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

COMMENT ON TABLE goals IS 'Founder goal submissions. DDD §2, PRD FR-1.1-1.4. Persisted before processing begins.';
