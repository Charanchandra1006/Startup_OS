-- ============================================================================
-- Chief AI Startup OS — Operational Store
-- Migration 007: Create Approval Requests Table
-- Implements: DDD §2 (ApprovalRequest entity), SGD §2, WDD §3
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

COMMENT ON TABLE approval_requests IS 'Pending/resolved approval decisions. DDD §2, SGD §2 approval-tier model, WDD §3.';
