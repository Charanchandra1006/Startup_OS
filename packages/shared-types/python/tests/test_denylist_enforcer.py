"""
Tests for Denylist Enforcer
Implements: Testing Strategy §2 (dedicated denylist test)

CRITICAL TEST: Asserts that the 6 hard-refusal actions can NEVER execute
via the automated executor, even if tier classification is buggy.
This test is specifically called out in Master Prompt §2 / §6.5.
"""

import pytest

from chief_types.denylist_enforcer import (
    check_denylist,
    assert_not_denied,
)
from chief_types.tier_classifier import HARD_DENIED_ACTION_TYPES


class TestDenylistEnforcement:
    """Test hard-refusal denylist enforcement."""

    @pytest.mark.parametrize("action_type", [
        "contract_sign",
        "wire_transfer",
        "offer_letter_send",
        "termination",
        "compensation_change",
        "public_statement",
    ])
    def test_all_six_denied_actions_are_blocked(self, action_type: str):
        """Each of the 6 hard-refusal actions is blocked."""
        result = check_denylist(action_type)
        assert result.is_denied, f"{action_type} must be denied"
        assert result.reason is not None
        assert len(result.reason) > 0

    @pytest.mark.parametrize("action_type", [
        "generate_report",
        "create_internal_draft",
        "publish_job_posting",
        "send_investor_email",
        "schedule_meeting",
    ])
    def test_non_denied_actions_pass(self, action_type: str):
        """Non-denylist actions are not blocked."""
        result = check_denylist(action_type)
        assert not result.is_denied

    @pytest.mark.parametrize("action_type", [
        "contract_sign",
        "wire_transfer",
        "offer_letter_send",
        "termination",
        "compensation_change",
        "public_statement",
    ])
    def test_assert_not_denied_raises_for_denied_actions(self, action_type: str):
        """assert_not_denied raises RuntimeError for denylist actions."""
        with pytest.raises(RuntimeError, match="HARD DENIAL"):
            assert_not_denied(action_type)

    def test_assert_not_denied_passes_for_allowed_actions(self):
        """assert_not_denied does not raise for allowed actions."""
        assert_not_denied("generate_report")  # Should not raise

    def test_denylist_reasons_are_specific(self):
        """Each denied action has a specific, meaningful reason."""
        for action_type in HARD_DENIED_ACTION_TYPES:
            result = check_denylist(action_type)
            assert result.reason is not None
            # Reason should mention the specific risk category
            assert len(result.reason) > 20, (
                f"Reason for {action_type} is too vague: '{result.reason}'"
            )

    def test_contract_sign_mentions_ng2(self):
        """contract_sign reason mentions NG-2 (no autonomous contract signing)."""
        result = check_denylist("contract_sign")
        assert "NG-2" in result.reason

    def test_wire_transfer_mentions_ng2(self):
        """wire_transfer reason mentions NG-2 (no autonomous money movement)."""
        result = check_denylist("wire_transfer")
        assert "NG-2" in result.reason

    def test_offer_letter_mentions_ng1(self):
        """offer_letter_send reason mentions NG-1 (no autonomous hiring decisions)."""
        result = check_denylist("offer_letter_send")
        assert "NG-1" in result.reason

    def test_termination_mentions_ng1(self):
        """termination reason mentions NG-1 (no autonomous firing decisions)."""
        result = check_denylist("termination")
        assert "NG-1" in result.reason

    def test_denylist_is_immutable(self):
        """The denylist set is a frozenset — cannot be modified at runtime."""
        assert isinstance(HARD_DENIED_ACTION_TYPES, frozenset)
