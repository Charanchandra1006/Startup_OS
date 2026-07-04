"""
Chief AI Startup OS — Grounding Validator
Implements: AIDD GR-01, NFR-007, Master Prompt §7

SHARED MIDDLEWARE: Used by every agent, not reimplemented per agent.

This validator ensures that no numeric or named-entity claim reaches a Report
or triggers a Tier-2/3 action without a resolvable citation or an explicit
"agent_inference, not sourced" tag.

This is enforced as a SCHEMA/PROGRAMMATIC check, not a prompt instruction.

Input: agent's raw LLM output text + structured claims
Output: either every claim resolves to {source_system, record_id} or is tagged
        agent_inference, or the claim is stripped from what reaches the
        Report/Action payload.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .models import AgentOutput, SupportingDataEntry


@dataclass
class GroundingValidationResult:
    """Result of grounding validation."""
    is_valid: bool
    validated_output: AgentOutput | None = None
    stripped_claims: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# Patterns that likely indicate a numeric/factual claim requiring citation
_NUMERIC_CLAIM_PATTERNS = [
    # Currency amounts: $X, €X, £X, etc.
    r'[\$€£¥]\s*[\d,]+(?:\.\d+)?(?:\s*[KkMmBbTt](?:illion|illion)?)?',
    # Percentages: X%, X percent
    r'\d+(?:\.\d+)?%',
    r'\d+(?:\.\d+)?\s*percent',
    # Numbers with units: X months, X days, X employees, etc.
    r'\d+(?:\.\d+)?\s+(?:months?|weeks?|days?|years?|employees?|headcount|engineers?|hires?)',
    # Dates: specific dates that reference events
    r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,?\s+\d{4})?',
    # Runway specifically (critical for finance agent)
    r'\d+(?:\.\d+)?\s+months?\s+(?:of\s+)?runway',
    # Burn rate
    r'burn\s+(?:rate\s+)?(?:of\s+)?[\$€£¥]?\s*[\d,]+',
    # Named entities that could be company/vendor specific
    r'(?:revenue|burn|runway|MRR|ARR|churn|NPS)\s+(?:is|was|of|at)\s+[\$€£¥]?\s*[\d,]+',
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _NUMERIC_CLAIM_PATTERNS]


def extract_claims_from_text(text: str) -> list[str]:
    """
    Extract numeric/factual claims from agent output text that require citation.
    Returns a list of matched claim strings.
    """
    claims = []
    for pattern in _COMPILED_PATTERNS:
        matches = pattern.findall(text)
        claims.extend(matches)
    return list(set(claims))  # Deduplicate


def _claim_is_grounded(
    claim: str,
    supporting_data: list[SupportingDataEntry],
) -> bool:
    """
    Check if a specific claim can be resolved to a supporting_data entry.
    A claim is grounded if:
    1. Its numeric value appears in a supporting_data entry's value field, OR
    2. The claim text is covered by a supporting_data entry from 'agent_inference' source
    """
    # Extract numeric value from claim for matching
    numbers_in_claim = re.findall(r'[\d,]+(?:\.\d+)?', claim)

    for entry in supporting_data:
        # Check if this is an agent_inference tag (explicitly allowed)
        if entry.source_system == "agent_inference":
            # Agent inference entries ground any claim they reference
            if claim.lower() in str(entry.source_ref).lower():
                return True
            if claim.lower() in str(entry.value).lower():
                return True

        # Check if any numeric value in the claim matches a supporting_data value
        entry_value_str = str(entry.value)
        for num in numbers_in_claim:
            # Normalize: remove commas for comparison
            normalized_num = num.replace(",", "")
            if normalized_num in entry_value_str.replace(",", ""):
                return True

    return False


def validate_grounding(output: AgentOutput) -> GroundingValidationResult:
    """
    Validate that every numeric/factual claim in an agent's output is grounded.

    This is the core enforcement function for NFR-007 / AIDD GR-01.
    Called on every agent output BEFORE it reaches synthesis.

    Rules:
    1. Extract all numeric/factual claims from the answer text
    2. Each claim must resolve to a supporting_data entry with
       {source_system, source_ref, value, retrieved_at}, OR
       be tagged as source_system='agent_inference'
    3. Ungrounded claims are STRIPPED from the output
    4. If all claims are stripped, the output is returned with caveats only

    Returns:
        GroundingValidationResult with validated output and any stripped claims
    """
    result = GroundingValidationResult(is_valid=True)

    # Extract claims from the answer text
    claims = extract_claims_from_text(output.answer)

    if not claims:
        # No numeric/factual claims found — output passes grounding check
        result.validated_output = output
        return result

    # Check if supporting_data exists when claims are present
    if not output.supporting_data and claims:
        result.is_valid = False
        result.errors.append(
            f"Output contains {len(claims)} numeric/factual claims but no supporting_data entries. "
            "Every claim requires a citation (AIDD GR-01, NFR-007)."
        )
        # Strip all claims from the answer
        stripped_answer = output.answer
        for claim in claims:
            stripped_answer = stripped_answer.replace(claim, "[CLAIM REMOVED — no citation]")
            result.stripped_claims.append(claim)

        result.validated_output = output.model_copy(update={
            "answer": stripped_answer,
            "caveats": output.caveats + [
                "Warning: numeric claims were removed from this output because they "
                "lacked supporting citations. See agent run details for original output."
            ],
        })
        return result

    # Validate each claim against supporting_data
    ungrounded_claims = []
    for claim in claims:
        if not _claim_is_grounded(claim, output.supporting_data):
            ungrounded_claims.append(claim)

    if ungrounded_claims:
        result.is_valid = False
        stripped_answer = output.answer
        for claim in ungrounded_claims:
            stripped_answer = stripped_answer.replace(
                claim, "[CLAIM REMOVED — no citation]"
            )
            result.stripped_claims.append(claim)
            result.errors.append(
                f"Ungrounded claim: '{claim}' — no matching supporting_data entry found"
            )

        result.validated_output = output.model_copy(update={
            "answer": stripped_answer,
            "caveats": output.caveats + [
                f"Warning: {len(ungrounded_claims)} numeric claim(s) were removed due to "
                "missing citations. See agent run details for original output."
            ],
        })
    else:
        # All claims grounded — output is valid
        result.validated_output = output

    return result


def validate_supporting_data_completeness(
    supporting_data: list[SupportingDataEntry],
) -> list[str]:
    """
    Validate that all supporting_data entries have the required fields.
    Returns a list of validation error messages (empty if all valid).
    """
    errors = []
    for i, entry in enumerate(supporting_data):
        if not entry.source_system:
            errors.append(f"supporting_data[{i}]: missing source_system")
        if not entry.source_ref:
            errors.append(f"supporting_data[{i}]: missing source_ref")
        if entry.value is None:
            errors.append(f"supporting_data[{i}]: missing value")
        if not entry.retrieved_at:
            errors.append(f"supporting_data[{i}]: missing retrieved_at")
    return errors
