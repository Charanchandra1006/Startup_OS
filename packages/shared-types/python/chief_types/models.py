"""
Chief AI Startup OS — Core Data Models
Implements: AIDD §2.1-2.3 (Agent I/O Contract), DDD §2 (Core Entities)

These Pydantic models are the single source of truth for the agent contract.
Every specialist agent's input/output must conform to these models.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ─── Enums ────────────────────────────────────────────────────────────────────

class GoalStatus(str, enum.Enum):
    RECEIVED = "received"
    CLASSIFYING = "classifying"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    DECOMPOSING = "decomposing"
    DISPATCHING = "dispatching"
    AWAITING_SPECIALIST_OUTPUT = "awaiting_specialist_output"
    SYNTHESIZING = "synthesizing"
    ROUTING_ACTIONS = "routing_actions"
    DELIVERED = "delivered"
    STALLED = "stalled"
    FAILED = "failed"


class GoalType(str, enum.Enum):
    REPORTING = "reporting"
    MONITORING = "monitoring"
    FORECASTING = "forecasting"
    AD_HOC_QUESTION = "ad_hoc_question"
    COMPOSITE = "composite"
    ACTION_REQUEST = "action_request"
    UNCLASSIFIED = "unclassified"


class ConfidenceLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskTier(str, enum.Enum):
    A = "A"  # Informational — no external effect
    B = "B"  # Reversible, low-impact
    C = "C"  # Reversible, external-facing
    D = "D"  # Irreversible or high-consequence


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    AUTO_EXECUTED = "auto_executed"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class InsightUrgency(str, enum.Enum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    URGENT = "urgent"


# ─── Agent Registry (AIDD §1) ────────────────────────────────────────────────

class AgentId(str, enum.Enum):
    """Platform-defined agent IDs from AIDD §1 registry."""
    FINANCE = "AGT-FIN"
    EXECUTIVE_ASSISTANT = "AGT-EA"
    PROJECT_MANAGEMENT = "AGT-PM"
    SALES = "AGT-SAL"
    CUSTOMER_SUCCESS = "AGT-CS"
    ANALYTICS = "AGT-ANL"
    HIRING = "AGT-HIR"
    ENGINEERING = "AGT-ENG"
    MARKETING = "AGT-MKT"
    LEGAL = "AGT-LEG"
    OPERATIONS = "AGT-OPS"
    RESEARCH = "AGT-RES"
    PRODUCT = "AGT-PRD"
    COMPLIANCE = "AGT-CMP"
    SECURITY = "AGT-SEC"
    COMPETITIVE_INTEL = "AGT-CI"
    KNOWLEDGE_MGMT = "AGT-KM"
    DOCUMENTATION = "AGT-DOC"
    ORCHESTRATOR = "AGT-ORC"
    ECHO = "AGT-ECHO"  # Phase 0 test agent


# ─── Supporting Data (AIDD §2.2) ─────────────────────────────────────────────

class SupportingDataEntry(BaseModel):
    """
    Citation for a numeric/factual claim.
    Every claim must map to one of these, or be tagged 'agent_inference'.
    Implements: AIDD §2.2, NFR-007, Master Prompt §7.
    """
    source_system: str = Field(
        ...,
        description="Which system this data came from (e.g., 'quickbooks', 'agent_inference')"
    )
    source_ref: str = Field(
        ...,
        description="Record/entity ID in the source system"
    )
    value: Any = Field(
        ...,
        description="The actual data value being cited"
    )
    retrieved_at: datetime = Field(
        ...,
        description="When this data was retrieved"
    )


# ─── Suggested Action (AIDD §2.3) ────────────────────────────────────────────

class SuggestedAction(BaseModel):
    """
    Agent-proposed action. This agent NEVER executes — only proposes.
    risk_tier is validated against platform lookup table (GR-04).
    """
    action_type: str = Field(
        ...,
        description="Platform-defined action type (not agent-defined)"
    )
    payload: dict[str, Any] = Field(
        ...,
        description="Exact content to be executed"
    )
    risk_tier: RiskTier = Field(
        ...,
        description="Set by platform lookup. Agent's value is validated and overridden if wrong."
    )
    rationale: str = Field(
        ...,
        description="Why this action is proposed, referencing supporting_data"
    )


# ─── Agent Input (AIDD §2.1) ─────────────────────────────────────────────────

class AgentInput(BaseModel):
    """Input contract for all specialist agents. AIDD §2.1."""
    goal_context: str = Field(
        ...,
        description="Founder's original goal text + orchestrator classification/decomposition"
    )
    scoped_data_access_token: str = Field(
        ...,
        description="Time-limited JWT for scoped data access. Never a standing credential."
    )
    task_description: str = Field(
        ...,
        description="The specific sub-task this agent invocation must complete"
    )
    tenant_id: UUID = Field(
        ...,
        description="Enforced at every downstream data call"
    )
    prior_context: list[UUID] = Field(
        default_factory=list,
        description="Prior AgentRun IDs relevant to this task"
    )
    playbook_refs: list[UUID] = Field(
        default_factory=list,
        description="PlaybookDocument IDs for RAG context"
    )


# ─── Agent Output (AIDD §2.2) ────────────────────────────────────────────────

class AgentOutput(BaseModel):
    """
    Output contract for all specialist agents. AIDD §2.2.
    Validated by the grounding gate before reaching synthesis.
    """
    answer: str = Field(
        ...,
        description="Founder-facing narrative answer"
    )
    supporting_data: list[SupportingDataEntry] = Field(
        default_factory=list,
        description="Mandatory citations. Required if answer contains numeric/factual claims."
    )
    confidence: ConfidenceLevel = Field(
        ...,
        description="Calibration checked against historical correction rate (AIDD §7)"
    )
    caveats: list[str] = Field(
        default_factory=list,
        description="Explicit scope gaps. May be empty, never omitted."
    )
    suggested_actions: list[SuggestedAction] = Field(
        default_factory=list,
        description="Proposals only — agent never executes"
    )
    model_used: str = Field(
        ...,
        description="Exact model identifier for reproducibility"
    )
    prompt_version: str = Field(
        ...,
        description="Semver for regression tracking (AIDD §8)"
    )

    @field_validator("prompt_version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        import re
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"prompt_version must be semver (x.y.z), got: {v}")
        return v


# ─── Report Content Contract (PVD §10) ───────────────────────────────────────

class ReportSections(BaseModel):
    """
    Fixed report structure per PVD §10.
    Every report must address these sections in order.
    Missing sections fail validation.
    """
    what_happened: str = Field(..., description="What changed / what occurred")
    why_it_happened: str = Field(..., description="Root cause / context")
    business_impact: str = Field(..., description="Impact on the business")
    risks: str = Field(..., description="Associated risks")
    recommendation: str = Field(..., description="What to do")
    alternatives_considered: str = Field(..., description="Other options evaluated")
    confidence: ConfidenceLevel = Field(..., description="Overall confidence level")
    next_actions: list[str] = Field(..., description="Suggested next steps")


# ─── Approval Request ────────────────────────────────────────────────────────

class ApprovalRequestModel(BaseModel):
    """Approval request for an action. SGD §2, WDD §3."""
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    action_type: str
    risk_tier: RiskTier
    diff_preview: dict[str, Any] = Field(
        ...,
        description="MUST be byte-for-byte identical to what will be executed (PRD FR-6.2)"
    )
    payload: dict[str, Any]
    rationale: str
    contributing_agents: list[str] = Field(default_factory=list)
    status: ApprovalStatus = ApprovalStatus.PENDING
    decided_by_user_id: Optional[UUID] = None
    decided_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


# ─── Execution Log Entry ─────────────────────────────────────────────────────

class ExecutionLogEntry(BaseModel):
    """Append-only execution audit log entry. DDD §5, NFR-004."""
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    approval_request_id: UUID
    action_type: str
    target_system: str
    payload_hash: str
    payload_snapshot: dict[str, Any]
    result_status: str  # success, failed, partial
    result_detail: Optional[dict[str, Any]] = None
    rollback_ref: Optional[str] = None
    previous_entry_hash: Optional[str] = None
    entry_hash: str = ""
    trace_id: Optional[str] = None
    executed_by_user_id: UUID = Field(...)
    risk_tier: RiskTier = Field(...)
    executed_at: datetime = Field(default_factory=datetime.utcnow)
