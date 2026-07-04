"""
Tests for Tier Classifier
Implements: Testing Strategy §2 (approval-tier testing)

Tests that:
1. Platform tier lookup works correctly for all action types
2. Agent-proposed tier is overridden when it disagrees with platform
3. Hard-denied actions are flagged
4. Unknown action types raise ValueError (schema-first enforcement)
5. Auto-execute eligibility follows SGD §2 rules
"""

import pytest

from chief_types.models import RiskTier
from chief_types.tier_classifier import (
    classify_action_tier,
    is_auto_execute_eligible,
    HARD_DENIED_ACTION_TYPES,
)


class TestTierClassification:
    """Test platform-level tier classification."""

    def test_tier_a_action(self):
        result = classify_action_tier("generate_report")
        assert result.effective_tier == RiskTier.A
        assert not result.is_hard_denied

    def test_tier_b_action(self):
        result = classify_action_tier("create_internal_draft")
        assert result.effective_tier == RiskTier.B
        assert not result.is_hard_denied

    def test_tier_c_action(self):
        result = classify_action_tier("publish_job_posting")
        assert result.effective_tier == RiskTier.C
        assert not result.is_hard_denied

    def test_tier_d_action(self):
        result = classify_action_tier("send_investor_email")
        assert result.effective_tier == RiskTier.D
        assert not result.is_hard_denied

    def test_agent_proposed_tier_overridden(self):
        """AIDD GR-04: Agent-proposed tier is overridden if it disagrees."""
        result = classify_action_tier(
            "send_investor_email",
            agent_proposed_tier=RiskTier.B,  # Agent tries to claim Tier B
        )
        # Platform says Tier D — agent's proposal is overridden
        assert result.effective_tier == RiskTier.D
        assert result.was_overridden
        assert result.agent_proposed_tier == RiskTier.B
        assert result.platform_tier == RiskTier.D

    def test_agent_proposed_tier_matches(self):
        """No override when agent proposes the correct tier."""
        result = classify_action_tier(
            "generate_report",
            agent_proposed_tier=RiskTier.A,
        )
        assert result.effective_tier == RiskTier.A
        assert not result.was_overridden

    def test_unknown_action_type_raises(self):
        """Schema-first: unknown action types must be registered first."""
        with pytest.raises(ValueError, match="Unknown action_type"):
            classify_action_tier("some_unknown_action")


class TestHardDeniedActions:
    """Test hard-refusal denylist classification."""

    def test_all_six_denied_actions_exist(self):
        """Master Prompt §6.5: exactly 6 hard-denied action types."""
        assert len(HARD_DENIED_ACTION_TYPES) == 6
        assert "contract_sign" in HARD_DENIED_ACTION_TYPES
        assert "wire_transfer" in HARD_DENIED_ACTION_TYPES
        assert "offer_letter_send" in HARD_DENIED_ACTION_TYPES
        assert "termination" in HARD_DENIED_ACTION_TYPES
        assert "compensation_change" in HARD_DENIED_ACTION_TYPES
        assert "public_statement" in HARD_DENIED_ACTION_TYPES

    @pytest.mark.parametrize("action_type", [
        "contract_sign",
        "wire_transfer",
        "offer_letter_send",
        "termination",
        "compensation_change",
        "public_statement",
    ])
    def test_each_denied_action_is_flagged(self, action_type: str):
        """Each denylist action is correctly flagged as hard_denied."""
        result = classify_action_tier(action_type)
        assert result.is_hard_denied, f"{action_type} should be hard-denied"
        assert result.effective_tier == RiskTier.D

    @pytest.mark.parametrize("action_type", [
        "contract_sign",
        "wire_transfer",
        "offer_letter_send",
        "termination",
        "compensation_change",
        "public_statement",
    ])
    def test_denied_actions_flagged_even_if_agent_claims_lower_tier(self, action_type: str):
        """Denylist enforcement is independent of agent-proposed tier."""
        result = classify_action_tier(action_type, agent_proposed_tier=RiskTier.A)
        assert result.is_hard_denied
        assert result.effective_tier == RiskTier.D
        assert result.was_overridden


class TestAutoExecuteEligibility:
    """Test auto-execute eligibility per SGD §2."""

    def test_tier_a_eligible(self):
        assert is_auto_execute_eligible("generate_report")

    def test_tier_b_eligible(self):
        assert is_auto_execute_eligible("create_internal_draft")

    def test_tier_c_not_eligible(self):
        assert not is_auto_execute_eligible("publish_job_posting")

    def test_tier_d_not_eligible(self):
        assert not is_auto_execute_eligible("send_investor_email")

    @pytest.mark.parametrize("action_type", list(HARD_DENIED_ACTION_TYPES))
    def test_hard_denied_never_eligible(self, action_type: str):
        """Hard-denied actions are never eligible for auto-execute."""
        assert not is_auto_execute_eligible(action_type)
