"""
Chief AI Startup OS — Denylist Enforcer
Implements: Master Prompt §6.5, NG-1/NG-2

Hard-refusal denylist enforcement at the Tool/Integration Gateway layer,
INDEPENDENT of and IN ADDITION TO tier logic.

ContractSignAction, WireTransferAction, OfferLetterSendAction,
TerminationAction, CompensationChangeAction, PublicStatementAction
are enforced as a denylist — these can NEVER execute via the automated
executor, even if tier classification is buggy.
"""

from __future__ import annotations

from dataclasses import dataclass

from .tier_classifier import HARD_DENIED_ACTION_TYPES


@dataclass
class DenylistCheckResult:
    """Result of checking an action against the hard-refusal denylist."""
    action_type: str
    is_denied: bool
    reason: str | None = None


def check_denylist(action_type: str) -> DenylistCheckResult:
    """
    Check if an action type is on the hard-refusal denylist.

    This check runs at the Tool/Integration Gateway layer, INDEPENDENTLY
    of tier classification. Even if the tier_rules table is corrupted or
    the tier classifier has a bug, this gate prevents execution.

    This is defense in depth — the denylist is checked at multiple layers:
    1. Here, at the gateway level
    2. In the Execution Service (separate check)
    3. In the tier_rules DB table (is_hard_denied flag)

    Args:
        action_type: The action type to check

    Returns:
        DenylistCheckResult indicating whether the action is denied
    """
    if action_type in HARD_DENIED_ACTION_TYPES:
        reasons = {
            "contract_sign": (
                "NG-2: No code path may sign contracts autonomously. "
                "This action requires human execution outside the platform."
            ),
            "wire_transfer": (
                "NG-2: No code path may move money autonomously. "
                "Wire transfers require human initiation outside the platform."
            ),
            "offer_letter_send": (
                "NG-1: No code path may make a hiring decision autonomously. "
                "Offer letters require human review and manual sending."
            ),
            "termination": (
                "NG-1: No code path may make a firing decision autonomously. "
                "Terminations are exclusively human decisions and actions."
            ),
            "compensation_change": (
                "NG-1/NG-2: Compensation changes are high-consequence "
                "decisions requiring human judgment and manual execution."
            ),
            "public_statement": (
                "Irreversible reputational risk. Public statements require "
                "human review and must be issued through human-controlled channels."
            ),
        }
        return DenylistCheckResult(
            action_type=action_type,
            is_denied=True,
            reason=reasons.get(action_type, "Action type is on the hard-refusal denylist"),
        )

    return DenylistCheckResult(
        action_type=action_type,
        is_denied=False,
    )


def assert_not_denied(action_type: str) -> None:
    """
    Assert that an action type is NOT on the denylist.
    Raises RuntimeError if denied — this is a hard failure, not a warning.

    Use this at enforcement points where denied actions should cause
    an immediate stop, not a soft rejection.
    """
    result = check_denylist(action_type)
    if result.is_denied:
        raise RuntimeError(
            f"HARD DENIAL: Action type '{action_type}' is on the hard-refusal denylist. "
            f"Reason: {result.reason}. "
            "This action can NEVER execute via the automated executor, "
            "regardless of tier classification or tenant configuration."
        )
