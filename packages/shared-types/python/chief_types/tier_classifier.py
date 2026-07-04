"""
Chief AI Startup OS — Tier Classifier
Implements: AIDD GR-04, SGD §2

Platform-level tier classification. Risk tiers are properties of action_types,
set by the platform — NOT overridable by agent or tenant configuration.

An agent cannot self-declare a lower tier to bypass friction.
"""

from __future__ import annotations

from .models import RiskTier

# ─── Hard-coded denylist (Master Prompt §6.5) ────────────────────────────────
# These are ALSO stored in the tier_rules DB table, but we maintain a code-level
# constant as defense in depth. Even if the DB is misconfigured, these are blocked.
HARD_DENIED_ACTION_TYPES: frozenset[str] = frozenset({
    "contract_sign",
    "wire_transfer",
    "offer_letter_send",
    "termination",
    "compensation_change",
    "public_statement",
})

# ─── Platform tier rules (loaded from DB in production, static fallback here)
# This is the authoritative mapping. Agents' proposed tiers are validated
# against this and overridden if they disagree.
_PLATFORM_TIER_RULES: dict[str, RiskTier] = {
    # Tier A — Informational
    "generate_report": RiskTier.A,
    "generate_insight": RiskTier.A,
    "generate_forecast": RiskTier.A,
    "generate_summary": RiskTier.A,
    # Tier B — Reversible, low-impact
    "create_internal_draft": RiskTier.B,
    "create_pm_task": RiskTier.B,
    "update_internal_note": RiskTier.B,
    # Tier C — Reversible, external-facing
    "publish_job_posting": RiskTier.C,
    "schedule_meeting": RiskTier.C,
    "schedule_interview": RiskTier.C,
    "send_candidate_communication": RiskTier.C,
    # Tier D — Irreversible or high-consequence
    "send_investor_email": RiskTier.D,
    "send_external_email": RiskTier.D,
    "distribute_board_deck": RiskTier.D,
    "send_investor_update": RiskTier.D,
    # Hard-denied (also Tier D, but blocked independently)
    "contract_sign": RiskTier.D,
    "wire_transfer": RiskTier.D,
    "offer_letter_send": RiskTier.D,
    "termination": RiskTier.D,
    "compensation_change": RiskTier.D,
    "public_statement": RiskTier.D,
}


class TierClassificationResult:
    """Result of tier classification for an action type."""

    def __init__(
        self,
        action_type: str,
        platform_tier: RiskTier,
        agent_proposed_tier: RiskTier | None = None,
        was_overridden: bool = False,
        is_hard_denied: bool = False,
    ):
        self.action_type = action_type
        self.platform_tier = platform_tier
        self.agent_proposed_tier = agent_proposed_tier
        self.was_overridden = was_overridden
        self.is_hard_denied = is_hard_denied

    @property
    def effective_tier(self) -> RiskTier:
        """The tier that should be used. Always the platform tier."""
        return self.platform_tier


def classify_action_tier(
    action_type: str,
    agent_proposed_tier: RiskTier | None = None,
    tier_rules_override: dict[str, RiskTier] | None = None,
) -> TierClassificationResult:
    """
    Classify an action's risk tier using platform-level rules.

    This is the ONLY way to determine an action's tier. Agents propose,
    the platform decides. Any mismatch is logged for prompt-tuning review.

    Args:
        action_type: The platform-defined action type string
        agent_proposed_tier: What the agent thinks the tier should be (validated, not trusted)
        tier_rules_override: Optional override for testing (normally loaded from DB)

    Returns:
        TierClassificationResult with the platform-assigned tier

    Raises:
        ValueError: If action_type is not recognized (new action types must be
                     registered in tier_rules before agents can propose them)
    """
    rules = tier_rules_override or _PLATFORM_TIER_RULES

    if action_type not in rules:
        raise ValueError(
            f"Unknown action_type '{action_type}'. "
            "New action types must be registered in tier_rules before use. "
            "This is a schema-first requirement (Master Prompt §6)."
        )

    platform_tier = rules[action_type]
    is_denied = action_type in HARD_DENIED_ACTION_TYPES
    was_overridden = (
        agent_proposed_tier is not None
        and agent_proposed_tier != platform_tier
    )

    return TierClassificationResult(
        action_type=action_type,
        platform_tier=platform_tier,
        agent_proposed_tier=agent_proposed_tier,
        was_overridden=was_overridden,
        is_hard_denied=is_denied,
    )


def is_auto_execute_eligible(action_type: str) -> bool:
    """
    Check if an action type is eligible for auto-execution.

    SGD §2 rules:
    - Tier A: always auto-execute (informational, no external effect)
    - Tier B: may be opted into auto-execute per tenant, per action type
    - Tier C: never auto-execute in Phase 1/2
    - Tier D: never auto-execute at any phase
    """
    result = classify_action_tier(action_type)

    if result.is_hard_denied:
        return False

    return result.platform_tier in (RiskTier.A, RiskTier.B)
