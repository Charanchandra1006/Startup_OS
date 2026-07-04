-- ============================================================================
-- Chief AI Startup OS — Seed Data: Tier Rules + Hard-Refusal Denylist
-- Implements: AIDD §2.3/GR-04, SGD §2, Master Prompt §6.5
--
-- CRITICAL: The hard-refusal denylist (is_hard_denied = true) entries are
-- enforced at the Tool/Integration Gateway layer INDEPENDENTLY of tier logic.
-- Even if tier classification is buggy, these actions can NEVER execute.
-- ============================================================================

-- === TIER A: Informational (no external effect) ===
INSERT INTO tier_rules (action_type, risk_tier, description, auto_execute_eligible, is_hard_denied)
VALUES
    ('generate_report', 'A', 'Generate an internal report/analysis', true, false),
    ('generate_insight', 'A', 'Generate a proactive insight for the feed', true, false),
    ('generate_forecast', 'A', 'Generate a forward financial forecast', true, false),
    ('generate_summary', 'A', 'Generate a structured summary of data', true, false)
ON CONFLICT (action_type) DO NOTHING;

-- === TIER B: Reversible, low-impact ===
INSERT INTO tier_rules (action_type, risk_tier, description, auto_execute_eligible, is_hard_denied)
VALUES
    ('create_internal_draft', 'B', 'Create a draft document internally', true, false),
    ('create_pm_task', 'B', 'Create a task in a project management tool', true, false),
    ('update_internal_note', 'B', 'Update an internal note or document', true, false)
ON CONFLICT (action_type) DO NOTHING;

-- === TIER C: Reversible, external-facing ===
INSERT INTO tier_rules (action_type, risk_tier, description, auto_execute_eligible, is_hard_denied)
VALUES
    ('publish_job_posting', 'C', 'Publish a job posting to an external job board', false, false),
    ('schedule_meeting', 'C', 'Schedule a meeting via calendar integration', false, false),
    ('schedule_interview', 'C', 'Schedule a candidate interview', false, false),
    ('send_candidate_communication', 'C', 'Send communication to a job candidate', false, false)
ON CONFLICT (action_type) DO NOTHING;

-- === TIER D: Irreversible or high-consequence ===
INSERT INTO tier_rules (action_type, risk_tier, description, auto_execute_eligible, is_hard_denied)
VALUES
    ('send_investor_email', 'D', 'Send email to investor/board member', false, false),
    ('send_external_email', 'D', 'Send any external email on behalf of the company', false, false),
    ('distribute_board_deck', 'D', 'Distribute a board deck to board members', false, false),
    ('send_investor_update', 'D', 'Send an investor update communication', false, false)
ON CONFLICT (action_type) DO NOTHING;

-- ============================================================================
-- HARD-REFUSAL DENYLIST (Master Prompt §6.5)
-- These 6 action types can NEVER execute via the automated executor,
-- regardless of tier classification. Enforced at the Tool Gateway layer
-- INDEPENDENTLY of and IN ADDITION TO tier logic.
-- ============================================================================
INSERT INTO tier_rules (action_type, risk_tier, description, auto_execute_eligible, is_hard_denied)
VALUES
    ('contract_sign', 'D', 'HARD DENIED: Sign a contract on behalf of the company', false, true),
    ('wire_transfer', 'D', 'HARD DENIED: Initiate a wire transfer or money movement', false, true),
    ('offer_letter_send', 'D', 'HARD DENIED: Send an offer letter to a candidate', false, true),
    ('termination', 'D', 'HARD DENIED: Terminate an employee', false, true),
    ('compensation_change', 'D', 'HARD DENIED: Change employee compensation', false, true),
    ('public_statement', 'D', 'HARD DENIED: Issue a public statement on behalf of the company', false, true)
ON CONFLICT (action_type) DO NOTHING;
