"""
Tests for Approval Workflow Service
"""

import pytest
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'packages', 'shared-types', 'python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from chief_types.models import RiskTier, ApprovalStatus
from chief_types.observability import reset_tracer
from approval_workflow import ApprovalWorkflowService, ApprovalDecision


TENANT_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
USER_ID = "b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22"


@pytest.fixture(autouse=True)
def reset():
    reset_tracer()


@pytest.fixture
def service():
    return ApprovalWorkflowService()


def _create_request(svc, action_type="publish_job_posting", tier=RiskTier.C):
    return svc.create_request(
        tenant_id=TENANT_ID,
        action_type=action_type,
        risk_tier=tier,
        diff_preview={"action_type": action_type, "payload": {"test": True}},
        payload={"test": True},
        rationale="Test rationale",
    )


class TestApprovalLifecycle:

    def test_create_request(self, service):
        req = _create_request(service)
        assert req.status == ApprovalStatus.PENDING
        assert req.expires_at is not None

    def test_approve(self, service):
        req = _create_request(service)
        result = service.decide(
            req.id,
            ApprovalDecision(user_id=USER_ID, approved=True),
        )
        assert result.status == ApprovalStatus.APPROVED
        assert result.decided_by_user_id == USER_ID

    def test_reject_with_reason(self, service):
        req = _create_request(service)
        result = service.decide(
            req.id,
            ApprovalDecision(user_id=USER_ID, approved=False, reason="Not now"),
        )
        assert result.status == ApprovalStatus.REJECTED
        assert result.rejection_reason == "Not now"

    def test_cannot_decide_twice(self, service):
        req = _create_request(service)
        service.decide(req.id, ApprovalDecision(user_id=USER_ID, approved=True))
        with pytest.raises(ValueError, match="already"):
            service.decide(req.id, ApprovalDecision(user_id=USER_ID, approved=True))

    def test_expired_request_cannot_be_decided(self, service):
        req = _create_request(service)
        # Force expiration
        req.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        with pytest.raises(ValueError, match="expired"):
            service.decide(req.id, ApprovalDecision(user_id=USER_ID, approved=True))


class TestPendingRequests:

    def test_pending_sorted_by_tier_priority(self, service):
        """Tier D requests should appear first."""
        _create_request(service, "create_internal_draft", RiskTier.B)
        _create_request(service, "send_investor_email", RiskTier.D)
        _create_request(service, "publish_job_posting", RiskTier.C)

        pending = service.get_pending_for_tenant(TENANT_ID)
        tiers = [r.risk_tier for r in pending]
        assert tiers == [RiskTier.D, RiskTier.C, RiskTier.B]

    def test_expired_filtered_from_pending(self, service):
        req = _create_request(service)
        req.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        pending = service.get_pending_for_tenant(TENANT_ID)
        assert len(pending) == 0


class TestExpiration:

    def test_expire_stale_requests(self, service):
        req = _create_request(service)
        req.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        expired = service.expire_stale_requests()
        assert req.id in expired
        assert service.get_request(req.id).status == ApprovalStatus.EXPIRED


class TestHistory:

    def test_history_includes_decided_requests(self, service):
        req = _create_request(service)
        service.decide(req.id, ApprovalDecision(user_id=USER_ID, approved=True))

        history = service.get_history_for_tenant(TENANT_ID)
        assert len(history) == 1
        assert history[0].status == ApprovalStatus.APPROVED
