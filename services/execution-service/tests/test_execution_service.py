"""
Tests for Execution Service
Implements: Testing Strategy §2 (approval/execution path testing)

CRITICAL TESTS:
- test_fail_closed: Audit log failure → action does NOT execute
- test_denylist: All 6 hard-denied actions blocked at executor level
- test_approval_tiers: All 4 tiers behave correctly
- test_diff_preview: Preview content = executed content
"""

import pytest
import uuid
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'packages', 'shared-types', 'python'))

from chief_types.models import RiskTier, SuggestedAction, ApprovalStatus
from chief_types.observability import reset_tracer

# Add execution service to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from execution_service import (
    ExecutionService,
    AuditWriter,
    AuditLogWriteError,
    DenylistViolationError,
    ApprovalRequiredError,
    MockExternalExecutor,
)


TENANT_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
USER_ID = "b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22"


def _make_action(
    action_type: str = "generate_report",
    risk_tier: RiskTier = RiskTier.A,
    payload: dict | None = None,
) -> SuggestedAction:
    return SuggestedAction(
        action_type=action_type,
        payload=payload or {"content": "test", "target_system": "mock"},
        risk_tier=risk_tier,
        rationale="Test action",
    )


@pytest.fixture
def service():
    reset_tracer()
    return ExecutionService()


# ============================================================================
# CRITICAL TEST: Fail-Closed Behavior (TRD §2)
# ============================================================================

class TestFailClosed:
    """
    Test fail-closed behavior: if audit log write fails,
    the action does NOT execute. No exceptions to this rule.
    """

    def test_audit_log_failure_blocks_execution(self, service: ExecutionService):
        """CRITICAL: If audit log write fails, action must NOT execute."""
        # Set audit writer to fail
        service.audit_writer.set_should_fail(True)

        action = _make_action("generate_report", RiskTier.A)

        with pytest.raises(AuditLogWriteError):
            service.submit_action(action, TENANT_ID)

        # Verify: NO execution occurred
        assert len(service.executor.get_executions()) == 0

    def test_audit_log_failure_on_approved_action_blocks(self, service: ExecutionService):
        """Audit log failure blocks even after human approval."""
        # Submit Tier C action (requires approval)
        action = _make_action("publish_job_posting", RiskTier.C)
        result = service.submit_action(action, TENANT_ID)
        assert result.status == ApprovalStatus.PENDING
        approval_id = str(result.id)

        # Set audit writer to fail AFTER approval
        service.audit_writer.set_should_fail(True)

        with pytest.raises(AuditLogWriteError):
            service.approve_action(approval_id, USER_ID)

        # Verify: NO execution occurred
        assert len(service.executor.get_executions()) == 0

    def test_successful_audit_log_allows_execution(self, service: ExecutionService):
        """When audit log succeeds, execution proceeds."""
        action = _make_action("generate_report", RiskTier.A)
        result = service.submit_action(action, TENANT_ID)

        # Audit log succeeded → execution happened
        assert result.result_status == "success"
        assert len(service.executor.get_executions()) == 1
        assert len(service.audit_writer.get_log()) == 1


# ============================================================================
# CRITICAL TEST: Hard-Refusal Denylist (Master Prompt §6.5)
# ============================================================================

class TestDenylist:
    """
    Test that all 6 hard-refusal actions can NEVER execute via the
    automated executor, even if tier classification is buggy.
    """

    @pytest.mark.parametrize("action_type", [
        "contract_sign",
        "wire_transfer",
        "offer_letter_send",
        "termination",
        "compensation_change",
        "public_statement",
    ])
    def test_denied_action_cannot_execute(self, service: ExecutionService, action_type: str):
        """Each of the 6 denied actions raises DenylistViolationError."""
        action = _make_action(action_type, RiskTier.D)

        with pytest.raises(DenylistViolationError):
            service.submit_action(action, TENANT_ID)

        # Verify: NO execution, NO audit log entry
        assert len(service.executor.get_executions()) == 0
        assert len(service.audit_writer.get_log()) == 0

    @pytest.mark.parametrize("action_type", [
        "contract_sign",
        "wire_transfer",
        "offer_letter_send",
        "termination",
        "compensation_change",
        "public_statement",
    ])
    def test_denied_action_blocked_even_with_wrong_tier(
        self, service: ExecutionService, action_type: str
    ):
        """Denylist blocks even if agent claims Tier A (tier classification bug)."""
        action = _make_action(action_type, RiskTier.A)  # Deliberately wrong tier

        with pytest.raises(DenylistViolationError):
            service.submit_action(action, TENANT_ID)


# ============================================================================
# Approval Tier Tests (SGD §2)
# ============================================================================

class TestApprovalTiers:
    """Test approval-tier behavior for all 4 tiers."""

    def test_tier_a_auto_executes(self, service: ExecutionService):
        """Tier A (informational) auto-executes without approval."""
        action = _make_action("generate_report", RiskTier.A)
        result = service.submit_action(action, TENANT_ID)

        # Should auto-execute and return ExecutionLogEntry
        assert hasattr(result, "result_status")
        assert result.result_status == "success"

    def test_tier_b_requires_approval_by_default(self, service: ExecutionService):
        """Tier B requires approval unless tenant opts in to auto-execute."""
        action = _make_action("create_internal_draft", RiskTier.B)
        result = service.submit_action(action, TENANT_ID)

        # Should return ApprovalRequest (not auto-executed)
        assert result.status == ApprovalStatus.PENDING

    def test_tier_b_auto_executes_when_opted_in(self, service: ExecutionService):
        """Tier B auto-executes when tenant has explicitly opted in."""
        service.set_tenant_auto_execute(TENANT_ID, "create_internal_draft", True)
        action = _make_action("create_internal_draft", RiskTier.B)
        result = service.submit_action(action, TENANT_ID)

        # Should auto-execute
        assert hasattr(result, "result_status")
        assert result.result_status == "success"

    def test_tier_c_requires_approval(self, service: ExecutionService):
        """Tier C ALWAYS requires approval (no auto-execute in Phase 1/2)."""
        action = _make_action("publish_job_posting", RiskTier.C)
        result = service.submit_action(action, TENANT_ID)

        assert result.status == ApprovalStatus.PENDING

    def test_tier_c_cannot_be_auto_executed(self, service: ExecutionService):
        """Tier C cannot be opted into auto-execute."""
        with pytest.raises(ValueError, match="Only Tier A/B"):
            service.set_tenant_auto_execute(TENANT_ID, "publish_job_posting", True)

    def test_tier_d_requires_approval(self, service: ExecutionService):
        """Tier D ALWAYS requires approval (never eligible for auto-execute)."""
        action = _make_action("send_investor_email", RiskTier.D)
        result = service.submit_action(action, TENANT_ID)

        assert result.status == ApprovalStatus.PENDING

    def test_tier_d_cannot_be_auto_executed(self, service: ExecutionService):
        """Tier D cannot be opted into auto-execute."""
        with pytest.raises(ValueError, match="Only Tier A/B"):
            service.set_tenant_auto_execute(TENANT_ID, "send_investor_email", True)


# ============================================================================
# Tier Override Tests (AIDD GR-04)
# ============================================================================

class TestTierOverride:
    """Test that platform tier overrides agent-proposed tier."""

    def test_agent_proposed_lower_tier_is_overridden(self, service: ExecutionService):
        """An agent claiming Tier B for a Tier D action gets overridden."""
        action = _make_action(
            "send_investor_email",
            RiskTier.B,  # Agent claims Tier B
        )
        result = service.submit_action(action, TENANT_ID)

        # Platform says Tier D → requires approval
        assert result.status == ApprovalStatus.PENDING
        assert result.risk_tier == RiskTier.D


# ============================================================================
# Approval Lifecycle Tests
# ============================================================================

class TestApprovalLifecycle:
    """Test the full approve/reject lifecycle."""

    def test_approve_and_execute(self, service: ExecutionService):
        """Full happy path: submit → approve → execute → audit log."""
        action = _make_action("publish_job_posting", RiskTier.C)
        approval = service.submit_action(action, TENANT_ID)
        assert approval.status == ApprovalStatus.PENDING

        result = service.approve_action(str(approval.id), USER_ID)
        assert result.result_status == "success"
        assert len(service.audit_writer.get_log()) == 1
        assert len(service.executor.get_executions()) == 1

    def test_reject_action(self, service: ExecutionService):
        """Rejected action is logged, NOT executed."""
        action = _make_action("publish_job_posting", RiskTier.C)
        approval = service.submit_action(action, TENANT_ID)

        result = service.reject_action(str(approval.id), USER_ID, "Not now")
        assert result.status == ApprovalStatus.REJECTED
        assert result.rejection_reason == "Not now"
        assert len(service.executor.get_executions()) == 0

    def test_double_approve_rejected(self, service: ExecutionService):
        """Cannot approve an already-approved action."""
        action = _make_action("schedule_meeting", RiskTier.C)
        approval = service.submit_action(action, TENANT_ID)
        service.approve_action(str(approval.id), USER_ID)

        with pytest.raises(ValueError, match="not pending"):
            service.approve_action(str(approval.id), USER_ID)


# ============================================================================
# Diff Preview Tests (PRD FR-6.2)
# ============================================================================

class TestDiffPreview:
    """Test that preview content = executed content (byte-for-byte)."""

    def test_preview_matches_payload(self, service: ExecutionService):
        """The diff_preview must contain the exact payload that will be executed."""
        payload = {
            "target_system": "gmail",
            "to": "investor@example.com",
            "subject": "Q4 Update",
            "body": "Dear Board,\n\nHere are the Q4 results...",
        }
        action = _make_action("send_investor_email", RiskTier.D, payload)
        approval = service.submit_action(action, TENANT_ID)

        # Verify preview contains exact payload
        assert approval.diff_preview["payload"] == payload
        assert approval.payload == payload


# ============================================================================
# Audit Log Integrity Tests
# ============================================================================

class TestAuditLogIntegrity:
    """Test audit log hash chaining and integrity."""

    def test_hash_chain_integrity(self, service: ExecutionService):
        """Audit log entries are hash-chained for tamper detection."""
        # Execute multiple actions
        for i in range(3):
            action = _make_action("generate_report", RiskTier.A, {"i": i, "target_system": "mock"})
            service.submit_action(action, TENANT_ID)

        log = service.audit_writer.get_log()
        assert len(log) == 3

        # First entry's previous hash is "genesis"
        assert log[0].previous_entry_hash == "genesis"

        # Subsequent entries chain to the previous
        for i in range(1, len(log)):
            assert log[i].previous_entry_hash == log[i - 1].entry_hash

        # All entry hashes are non-empty and unique
        hashes = [e.entry_hash for e in log]
        assert all(h for h in hashes)
        assert len(set(hashes)) == len(hashes)
