"""
Chief AI Startup OS — Execution Service
Implements: WDD §3, SGD §2, PRD FR-6.1/6.2/6.3, TRD §2

The SOLE holder of external write credentials. No specialist agent or
orchestrator calls an external write API directly — only this service does.

CRITICAL NON-NEGOTIABLE:
- Every execution has a corresponding audit log entry (fail-closed)
- If audit log write fails, the action does NOT execute
- Hard-refusal denylist is enforced here AS WELL AS at the Tool Gateway
- Tier classification uses platform rules, not agent proposals
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from chief_types.models import (
    ApprovalRequestModel,
    ApprovalStatus,
    ExecutionLogEntry,
    RiskTier,
    SuggestedAction,
)
from chief_types.denylist_enforcer import assert_not_denied, check_denylist
from chief_types.tier_classifier import classify_action_tier, is_auto_execute_eligible
from chief_types.observability import get_tracer

logger = logging.getLogger("chief.execution_service")


class AuditLogWriteError(Exception):
    """Raised when the audit log write fails. Action must NOT execute."""
    pass


class DenylistViolationError(Exception):
    """Raised when an action on the hard-refusal denylist is attempted."""
    pass


class ApprovalRequiredError(Exception):
    """Raised when an action requires human approval before execution."""
    pass


class AuditWriter:
    """
    Synchronous, fail-closed audit log writer.
    Implements: DDD §5, NFR-004, TRD §2.

    If this write fails, the action does NOT execute. No exceptions.
    In production, this writes to the execution_log table using
    the chief_execution_writer DB role (INSERT only, no UPDATE/DELETE).
    """

    def __init__(self):
        self._log: list[ExecutionLogEntry] = []  # In-memory for Phase 0
        self._should_fail: bool = False  # For testing fail-closed behavior

    def write(self, entry: ExecutionLogEntry) -> None:
        """
        Write an execution log entry. MUST succeed before action executes.

        Raises:
            AuditLogWriteError: If the write fails — action must NOT proceed.
        """
        if self._should_fail:
            raise AuditLogWriteError(
                "Audit log write failed. Action WILL NOT execute. "
                "This is fail-closed behavior per TRD §2."
            )

        # Compute hash chain
        if self._log:
            entry.previous_entry_hash = self._log[-1].entry_hash
        else:
            entry.previous_entry_hash = "genesis"

        # Compute entry hash (payload + previous hash + timestamp)
        hash_input = json.dumps({
            "payload_hash": entry.payload_hash,
            "previous_entry_hash": entry.previous_entry_hash,
            "executed_at": entry.executed_at.isoformat(),
            "action_type": entry.action_type,
        }, sort_keys=True)
        entry.entry_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        self._log.append(entry)
        logger.info(
            f"Audit log entry written: {entry.id} | "
            f"action={entry.action_type} | tier={entry.risk_tier} | "
            f"hash={entry.entry_hash[:16]}..."
        )

    def get_log(self) -> list[ExecutionLogEntry]:
        """Get all log entries (for testing/auditing)."""
        return list(self._log)

    def set_should_fail(self, should_fail: bool) -> None:
        """For testing: make the next write fail to test fail-closed behavior."""
        self._should_fail = should_fail


class MockExternalExecutor:
    """
    Mock external execution adapter for Phase 0.
    In production, this calls the Tool Gateway which routes to real integrations.
    """

    def __init__(self):
        self._executions: list[dict[str, Any]] = []

    def execute(
        self,
        action_type: str,
        target_system: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute an action against a target system."""
        execution_record = {
            "action_type": action_type,
            "target_system": target_system,
            "payload": payload,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "status": "success",
        }
        self._executions.append(execution_record)
        return {"status": "success", "detail": "Mock execution completed"}

    def get_executions(self) -> list[dict[str, Any]]:
        return list(self._executions)


class ExecutionService:
    """
    The Execution Service — sole holder of external write credentials.

    Workflow (WDD §3):
    1. Receive action from orchestrator with agent-proposed risk_tier
    2. Classify risk_tier using platform rules (override agent if wrong)
    3. Check hard-refusal denylist (independent of tier)
    4. Check tenant approval configuration for auto-execute eligibility
    5. If approval required → create ApprovalRequest, wait for human
    6. On approval → execute via Tool Gateway
    7. Write audit log SYNCHRONOUSLY before considering action complete
    8. If audit log write fails → action does NOT execute (fail-closed)
    """

    def __init__(
        self,
        audit_writer: AuditWriter | None = None,
        executor: MockExternalExecutor | None = None,
    ):
        self.audit_writer = audit_writer or AuditWriter()
        self.executor = executor or MockExternalExecutor()
        self._approval_requests: dict[str, ApprovalRequestModel] = {}
        self._tenant_auto_execute: dict[str, set[str]] = {}  # tenant_id → {action_types}
        self.tracer = get_tracer("execution-service")

    def submit_action(
        self,
        action: SuggestedAction,
        tenant_id: str,
        recommendation_id: str | None = None,
        contributing_agents: list[str] | None = None,
        trace_id: str | None = None,
    ) -> ApprovalRequestModel | ExecutionLogEntry:
        """
        Submit an action for approval/execution.

        Returns:
            ApprovalRequestModel if approval is required
            ExecutionLogEntry if action was auto-executed

        Raises:
            DenylistViolationError if action is on the hard-refusal denylist
        """
        with self.tracer.start_span(
            "execution_service.submit_action",
            trace_id=trace_id,
            tenant_id=tenant_id,
        ) as span:
            span.set_attribute("action.type", action.action_type)

            # Step 1: Check hard-refusal denylist (INDEPENDENT of tier)
            denylist_result = check_denylist(action.action_type)
            if denylist_result.is_denied:
                span.set_status("ERROR", f"HARD DENIAL: {action.action_type}")
                raise DenylistViolationError(
                    f"Action '{action.action_type}' is on the hard-refusal denylist. "
                    f"Reason: {denylist_result.reason}"
                )

            # Step 2: Classify tier using platform rules (override agent if wrong)
            tier_result = classify_action_tier(
                action.action_type,
                agent_proposed_tier=action.risk_tier,
            )
            platform_tier = tier_result.effective_tier
            span.set_attribute("action.platform_tier", platform_tier.value)

            if tier_result.was_overridden:
                span.add_event("tier_overridden", {
                    "agent_proposed": action.risk_tier.value,
                    "platform_assigned": platform_tier.value,
                })
                logger.warning(
                    f"Agent proposed tier {action.risk_tier.value} for {action.action_type}, "
                    f"overridden to {platform_tier.value} by platform rules"
                )

            # Step 3: Build the diff_preview (byte-identical to execution payload)
            diff_preview = self._build_diff_preview(action)

            # Step 4: Check auto-execute eligibility
            can_auto_execute = self._check_auto_execute(
                action.action_type, platform_tier, tenant_id
            )

            if can_auto_execute:
                # Auto-execute (Tier A always, Tier B if tenant opted in)
                span.add_event("auto_executing")
                return self._execute_and_log(
                    action=action,
                    platform_tier=platform_tier,
                    tenant_id=tenant_id,
                    approved_by_user_id="system_auto",
                    trace_id=trace_id or span.trace_id,
                )
            else:
                # Create approval request
                approval_request = ApprovalRequestModel(
                    id=uuid.uuid4(),
                    tenant_id=uuid.UUID(tenant_id),
                    action_type=action.action_type,
                    risk_tier=platform_tier,
                    diff_preview=diff_preview,
                    payload=action.payload,
                    rationale=action.rationale,
                    contributing_agents=contributing_agents or [],
                    status=ApprovalStatus.PENDING,
                )
                self._approval_requests[str(approval_request.id)] = approval_request
                span.add_event("approval_requested", {
                    "approval_id": str(approval_request.id),
                    "risk_tier": platform_tier.value,
                })
                return approval_request

    def approve_action(
        self,
        approval_request_id: str,
        user_id: str,
        trace_id: str | None = None,
    ) -> ExecutionLogEntry:
        """
        Approve and execute a pending action.

        Raises:
            AuditLogWriteError: If audit log write fails (action NOT executed)
        """
        request = self._approval_requests.get(approval_request_id)
        if not request:
            raise ValueError(f"Approval request {approval_request_id} not found")
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval request is {request.status.value}, not pending")

        request.status = ApprovalStatus.APPROVED
        request.decided_by_user_id = uuid.UUID(user_id)
        request.decided_at = datetime.now(timezone.utc)

        action = SuggestedAction(
            action_type=request.action_type,
            payload=request.payload,
            risk_tier=request.risk_tier,
            rationale=request.rationale,
        )

        return self._execute_and_log(
            action=action,
            platform_tier=request.risk_tier,
            tenant_id=str(request.tenant_id),
            approved_by_user_id=user_id,
            approval_request_id=approval_request_id,
            trace_id=trace_id,
        )

    def reject_action(
        self,
        approval_request_id: str,
        user_id: str,
        reason: str | None = None,
    ) -> ApprovalRequestModel:
        """Reject a pending action. No execution occurs."""
        request = self._approval_requests.get(approval_request_id)
        if not request:
            raise ValueError(f"Approval request {approval_request_id} not found")

        request.status = ApprovalStatus.REJECTED
        request.decided_by_user_id = uuid.UUID(user_id)
        request.rejection_reason = reason
        request.decided_at = datetime.now(timezone.utc)

        logger.info(
            f"Action rejected: {request.action_type} | "
            f"reason={reason or 'no reason given'}"
        )
        return request

    def set_tenant_auto_execute(
        self, tenant_id: str, action_type: str, enabled: bool
    ) -> None:
        """
        Set auto-execute preference for a tenant + action type.
        Only Tier B actions are eligible (SGD §2).
        """
        tier_result = classify_action_tier(action_type)
        if tier_result.effective_tier not in (RiskTier.A, RiskTier.B):
            raise ValueError(
                f"Cannot enable auto-execute for {action_type} "
                f"(Tier {tier_result.effective_tier.value}). "
                "Only Tier A/B actions are eligible per SGD §2."
            )

        if tenant_id not in self._tenant_auto_execute:
            self._tenant_auto_execute[tenant_id] = set()

        if enabled:
            self._tenant_auto_execute[tenant_id].add(action_type)
        else:
            self._tenant_auto_execute[tenant_id].discard(action_type)

    def _check_auto_execute(
        self, action_type: str, platform_tier: RiskTier, tenant_id: str
    ) -> bool:
        """Check if an action can be auto-executed."""
        # Tier A: always auto-execute (informational, no external effect)
        if platform_tier == RiskTier.A:
            return True

        # Tier B: only if tenant explicitly opted in for this action type
        if platform_tier == RiskTier.B:
            tenant_prefs = self._tenant_auto_execute.get(tenant_id, set())
            return action_type in tenant_prefs

        # Tier C/D: NEVER auto-execute (SGD §2)
        return False

    def _build_diff_preview(self, action: SuggestedAction) -> dict[str, Any]:
        """
        Build the diff/preview that will be shown to the founder.
        PRD FR-6.2: This MUST be byte-for-byte identical to what will be executed.
        """
        # The preview IS the payload — same object, ensuring byte-identical guarantee
        return {
            "action_type": action.action_type,
            "payload": action.payload,
            "rationale": action.rationale,
        }

    def _execute_and_log(
        self,
        action: SuggestedAction,
        platform_tier: RiskTier,
        tenant_id: str,
        approved_by_user_id: str,
        approval_request_id: str | None = None,
        trace_id: str | None = None,
    ) -> ExecutionLogEntry:
        """
        Execute an action and write to audit log.
        CRITICAL: Audit log write is SYNCHRONOUS and must succeed
        before the action is considered complete (fail-closed, TRD §2).
        """
        # Compute payload hash for tamper detection
        payload_json = json.dumps(action.payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()

        # Create the audit log entry FIRST
        log_entry = ExecutionLogEntry(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id),
            approval_request_id=uuid.UUID(approval_request_id) if approval_request_id else uuid.uuid4(),
            action_type=action.action_type,
            target_system=action.payload.get("target_system", "unknown"),
            payload_hash=payload_hash,
            payload_snapshot=action.payload,
            result_status="pending",
            trace_id=trace_id,
            executed_by_user_id=uuid.UUID(approved_by_user_id) if approved_by_user_id != "system_auto" else uuid.UUID("00000000-0000-0000-0000-000000000000"),
            risk_tier=platform_tier,
        )

        # CRITICAL: Write audit log SYNCHRONOUSLY. If this fails, do NOT execute.
        try:
            self.audit_writer.write(log_entry)
        except AuditLogWriteError:
            logger.error(
                f"FAIL-CLOSED: Audit log write failed for action {action.action_type}. "
                "Action will NOT be executed. TRD §2."
            )
            raise

        # Only now execute the actual action
        try:
            result = self.executor.execute(
                action_type=action.action_type,
                target_system=action.payload.get("target_system", "mock"),
                payload=action.payload,
            )
            log_entry.result_status = result.get("status", "success")
            log_entry.result_detail = result
        except Exception as e:
            log_entry.result_status = "failed"
            log_entry.result_detail = {"error": str(e)}
            logger.error(f"Execution failed for {action.action_type}: {e}")

        return log_entry
