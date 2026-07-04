"""
Tests for Grounding Validator
Implements: Testing Strategy §1.2 (grounding tests)

Tests that the grounding validator correctly:
1. Accepts fully grounded agent output
2. Strips ungrounded claims from output
3. Accepts 'agent_inference' tagged claims
4. Rejects output with numeric claims but no supporting_data
"""

import pytest
from datetime import datetime, timezone

from chief_types.models import AgentOutput, SupportingDataEntry, ConfidenceLevel
from chief_types.grounding_validator import (
    validate_grounding,
    extract_claims_from_text,
    validate_supporting_data_completeness,
)


def _make_output(
    answer: str,
    supporting_data: list[SupportingDataEntry] | None = None,
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
) -> AgentOutput:
    """Helper to create a valid AgentOutput for testing."""
    return AgentOutput(
        answer=answer,
        supporting_data=supporting_data or [],
        confidence=confidence,
        caveats=[],
        model_used="gpt-4o",
        prompt_version="1.0.0",
    )


def _make_citation(
    source: str = "quickbooks",
    ref: str = "txn_123",
    value: str = "50000",
    retrieved_at: datetime | None = None,
) -> SupportingDataEntry:
    """Helper to create a SupportingDataEntry."""
    return SupportingDataEntry(
        source_system=source,
        source_ref=ref,
        value=value,
        retrieved_at=retrieved_at or datetime.now(timezone.utc),
    )


class TestExtractClaims:
    """Test claim extraction from text."""

    def test_extracts_currency_amounts(self):
        claims = extract_claims_from_text("The burn rate is $50,000 per month")
        assert any("50,000" in c for c in claims)

    def test_extracts_percentages(self):
        claims = extract_claims_from_text("Revenue grew 25% this quarter")
        assert any("25%" in c for c in claims)

    def test_extracts_runway(self):
        claims = extract_claims_from_text("You have 8 months of runway remaining")
        assert any("8 months" in c.lower() for c in claims)

    def test_no_claims_in_plain_text(self):
        claims = extract_claims_from_text(
            "The team is making good progress on the project."
        )
        assert len(claims) == 0

    def test_extracts_burn_rate(self):
        claims = extract_claims_from_text("burn rate of $120,000")
        assert len(claims) > 0


class TestGroundingValidation:
    """Test the core grounding validation logic."""

    def test_passes_output_with_no_claims(self):
        """Output without numeric claims passes grounding check."""
        output = _make_output("The team is doing well on the project.")
        result = validate_grounding(output)
        assert result.is_valid
        assert result.validated_output is not None
        assert len(result.stripped_claims) == 0

    def test_passes_fully_grounded_output(self):
        """Output with all claims grounded passes."""
        output = _make_output(
            "The burn rate is $50,000 per month.",
            supporting_data=[
                _make_citation(value="50000"),
            ],
        )
        result = validate_grounding(output)
        assert result.is_valid
        assert len(result.stripped_claims) == 0

    def test_strips_ungrounded_claims(self):
        """Ungrounded claims are stripped from the output."""
        output = _make_output(
            "The burn rate is $50,000 per month. Revenue is $100,000.",
            supporting_data=[
                _make_citation(value="50000"),
                # No citation for $100,000
            ],
        )
        result = validate_grounding(output)
        assert not result.is_valid
        assert len(result.stripped_claims) > 0
        assert result.validated_output is not None
        assert "[CLAIM REMOVED" in result.validated_output.answer

    def test_rejects_claims_with_no_supporting_data(self):
        """Output with claims but empty supporting_data is rejected."""
        output = _make_output(
            "The burn rate is $50,000 per month.",
            supporting_data=[],
        )
        result = validate_grounding(output)
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_accepts_agent_inference_tagged_claims(self):
        """Claims tagged as agent_inference are accepted."""
        output = _make_output(
            "The burn rate is $50,000 per month.",
            supporting_data=[
                SupportingDataEntry(
                    source_system="agent_inference",
                    source_ref="Based on trend analysis of $50,000",
                    value="50000",
                    retrieved_at=datetime.now(timezone.utc),
                ),
            ],
        )
        result = validate_grounding(output)
        assert result.is_valid

    def test_adds_caveats_when_claims_stripped(self):
        """Stripped claims result in caveats being added."""
        output = _make_output(
            "Revenue grew 25% this quarter.",
            supporting_data=[],
        )
        result = validate_grounding(output)
        assert not result.is_valid
        assert result.validated_output is not None
        assert len(result.validated_output.caveats) > 0
        assert "removed" in result.validated_output.caveats[-1].lower()

    def test_preserves_original_caveats(self):
        """Original caveats are preserved when new ones are added."""
        output = _make_output(
            "Revenue grew 25% this quarter.",
            supporting_data=[],
        )
        output = output.model_copy(update={"caveats": ["No visibility into cash sales"]})
        result = validate_grounding(output)
        assert result.validated_output is not None
        assert "No visibility into cash sales" in result.validated_output.caveats


class TestSupportingDataCompleteness:
    """Test supporting_data field validation."""

    def test_valid_entry_passes(self):
        entry = _make_citation()
        errors = validate_supporting_data_completeness([entry])
        assert len(errors) == 0

    def test_missing_source_system(self):
        entry = SupportingDataEntry(
            source_system="",
            source_ref="txn_123",
            value="50000",
            retrieved_at=datetime.now(timezone.utc),
        )
        errors = validate_supporting_data_completeness([entry])
        assert any("source_system" in e for e in errors)

    def test_missing_source_ref(self):
        entry = SupportingDataEntry(
            source_system="quickbooks",
            source_ref="",
            value="50000",
            retrieved_at=datetime.now(timezone.utc),
        )
        errors = validate_supporting_data_completeness([entry])
        assert any("source_ref" in e for e in errors)
