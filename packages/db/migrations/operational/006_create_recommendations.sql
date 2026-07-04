-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- Migration 006: Create Recommendations Table
-- Implements: DDD §2 (Recommendation entity)
-- ============================================================================

CREATE TABLE IF NOT EXISTS recommendations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id                 UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    synthesized_text        TEXT NOT NULL,
    -- Report content contract (PVD §10): what_happened, why, impact, risks,
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

COMMENT ON TABLE recommendations IS 'Synthesized orchestrator output from specialist agent results. DDD §2, PVD §10 report contract.';
