"""
Chief AI Startup OS — Approval Workflow Service
Implements: WDD §3 (Approval lifecycle), SGD §2, PRD FR-6

Manages the lifecycle of approval requests:
- Pending → Approved | Rejected | Expired
- Tracks who approved, when, and why
- Expiration enforcement (auto-expire stale requests)
- Approval history and audit trail
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field

from chief_types.models import ApprovalStatus, RiskTier
from chief_types.observability import get_tracer

logger = logging.getLogger("chief.approval_workflow")


# ─── Models ──────────────────────────────────────────────────────────────────

class ApprovalRequest(BaseModel):
    """Full approval request record."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    goal_id: str | None = None
    recommendation_id: str | None = None
    action_type: str
    risk_tier: RiskTier
    diff_preview: dict[str, Any]
    payload: dict[str, Any]
    rationale: str
    contributing_agents: list[str] = Field(default_factory=list)
    status: ApprovalStatus = ApprovalStatus.PENDING
    decided_by_user_id: str | None = None
    rejection_reason: str | None = None
    decided_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: str | None = None


class ApprovalDecision(BaseModel):
    """A user's decision on an approval request."""
    user_id: str
    approved: bool
    reason: str | None = None


# ─── Expiration Config ────────────────────────────────────────────────────────

# Default expiration windows by tier (configurable)
DEFAULT_EXPIRY_HOURS: dict[RiskTier, int] = {
    RiskTier.A: 1,    # 1 hour — shouldn't usually need approval
    RiskTier.B: 24,   # 24 hours
    RiskTier.C: 72,   # 3 days
    RiskTier.D: 168,  # 7 days
}


# ─── Approval Workflow Service ────────────────────────────────────────────────

class ApprovalWorkflowService:
    """
    Manages the full lifecycle of approval requests.

    Lifecycle:
    1. CREATE — Execution Service creates a pending request
    2. NOTIFY — Founder is notified (pushed to UI insight feed)
    3. REVIEW — Founder sees diff_preview, rationale, contributing agents
    4. DECIDE — Founder approves or rejects (with optional reason)
    5. EXECUTE — On approval, Execution Service proceeds
    6. EXPIRE — Stale requests auto-expire per tier-based windows
    """

    def __init__(self):
        self._requests: dict[str, ApprovalRequest] = {}
        self.tracer = get_tracer("approval-workflow")

    def create_request(
        self,
        tenant_id: str,
        action_type: str,
        risk_tier: RiskTier,
        diff_preview: dict[str, Any],
        payload: dict[str, Any],
        rationale: str,
        contributing_agents: list[str] | None = None,
        goal_id: str | None = None,
        trace_id: str | None = None,
    ) -> ApprovalRequest:
        """Create a new pending approval request."""
        with self.tracer.start_span(
            "approval.create_request",
            tenant_id=tenant_id,
        ) as span:
            expiry_hours = DEFAULT_EXPIRY_HOURS.get(risk_tier, 72)
            now = datetime.now(timezone.utc)

            request = ApprovalRequest(
                tenant_id=tenant_id,
                goal_id=goal_id,
                action_type=action_type,
                risk_tier=risk_tier,
                diff_preview=diff_preview,
                payload=payload,
                rationale=rationale,
                contributing_agents=contributing_agents or [],
                expires_at=now + timedelta(hours=expiry_hours),
                trace_id=trace_id,
            )

            self._requests[request.id] = request
            span.set_attribute("approval.id", request.id)
            span.set_attribute("approval.tier", risk_tier.value)
            span.set_attribute("approval.expires_hours", expiry_hours)

            logger.info(
                f"Approval request created: id={request.id} "
                f"action={action_type} tier={risk_tier.value} "
                f"expires_in={expiry_hours}h"
            )
            return request

    def decide(
        self,
        request_id: str,
        decision: ApprovalDecision,
    ) -> ApprovalRequest:
        """
        Record a user's decision on an approval request.

        Raises:
            ValueError: If request not found, already decided, or expired.
        """
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Approval request '{request_id}' not found")

        if request.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Request '{request_id}' is already {request.status.value}"
            )

        # Check expiration before allowing decision
        now = datetime.now(timezone.utc)
        if request.expires_at and now > request.expires_at:
            request.status = ApprovalStatus.EXPIRED
            logger.info(f"Approval request {request_id} has expired")
            raise ValueError(f"Request '{request_id}' has expired")

        request.decided_by_user_id = decision.user_id
        request.decided_at = now

        if decision.approved:
            request.status = ApprovalStatus.APPROVED
            logger.info(
                f"Approval APPROVED: id={request_id} by={decision.user_id}"
            )
        else:
            request.status = ApprovalStatus.REJECTED
            request.rejection_reason = decision.reason
            logger.info(
                f"Approval REJECTED: id={request_id} by={decision.user_id} "
                f"reason={decision.reason or 'none given'}"
            )

        return request

    def get_pending_for_tenant(self, tenant_id: str) -> list[ApprovalRequest]:
        """Get all pending approval requests for a tenant, ordered by urgency."""
        now = datetime.now(timezone.utc)
        pending = []
        for req in self._requests.values():
            if req.tenant_id == tenant_id and req.status == ApprovalStatus.PENDING:
                # Check expiration
                if req.expires_at and now > req.expires_at:
                    req.status = ApprovalStatus.EXPIRED
                    continue
                pending.append(req)

        # Sort: highest tier first (D > C > B > A), then oldest first
        tier_order = {RiskTier.D: 0, RiskTier.C: 1, RiskTier.B: 2, RiskTier.A: 3}
        return sorted(
            pending,
            key=lambda r: (tier_order.get(r.risk_tier, 99), r.created_at),
        )

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)

    def get_history_for_tenant(
        self,
        tenant_id: str,
        limit: int = 50,
    ) -> list[ApprovalRequest]:
        """Get decided approval requests for a tenant (audit history)."""
        history = [
            req for req in self._requests.values()
            if req.tenant_id == tenant_id
            and req.status in (
                ApprovalStatus.APPROVED,
                ApprovalStatus.REJECTED,
                ApprovalStatus.EXPIRED,
            )
        ]
        return sorted(
            history,
            key=lambda r: r.decided_at or r.created_at,
            reverse=True,
        )[:limit]

    def expire_stale_requests(self) -> list[str]:
        """
        Expire all requests past their expiration window.
        Returns list of expired request IDs.
        Called periodically by the system (e.g., cron job or K8s CronJob).
        """
        now = datetime.now(timezone.utc)
        expired_ids = []
        for req in self._requests.values():
            if (
                req.status == ApprovalStatus.PENDING
                and req.expires_at
                and now > req.expires_at
            ):
                req.status = ApprovalStatus.EXPIRED
                expired_ids.append(req.id)
                logger.info(f"Auto-expired approval request: {req.id}")
        return expired_ids
