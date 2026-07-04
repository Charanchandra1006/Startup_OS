-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- Migration 011: Create Insight Feed Table
-- Implements: PRD FR-5.1/5.2, WDD §4 (proactive monitoring)
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
    why_it_matters  TEXT NOT NULL,           -- One-line "why this matters" (UXDS §2.1)
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

COMMENT ON TABLE insights IS 'Proactive insight feed items. PRD FR-5.1/5.2, WDD §4. Persistent until dismissed or acted upon.';
