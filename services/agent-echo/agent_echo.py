"""
Chief AI Startup OS — Echo Agent (Phase 0 Test Agent)
Implements: AIDD §2 (agent contract)

A trivial specialist agent that proves the full pipeline end-to-end.
Produces cited structured output with a dummy Tier C action to verify:
1. Agent contract compliance (AIDD §2.2 schema)
2. Grounding validation (GR-01)
3. Tier classification routing (GR-04)
4. Approval gate behavior (SGD §2)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any
from dotenv import load_dotenv

# Ensure packages can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../packages/shared-types/python')))
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env')))

from chief_types.models import (
    AgentInput,
    AgentOutput,
    ConfidenceLevel,
    RiskTier,
    SuggestedAction,
    SupportingDataEntry,
)
from chief_types.observability import get_tracer


AGENT_ID = "AGT-ECHO"
PROMPT_VERSION = "1.0.0"
MODEL_USED = "echo-model-v1"


async def process_task(task_input: AgentInput) -> AgentOutput:
    """
    Process a task per the AIDD §2 specialist agent contract.

    This echo agent:
    1. Returns a properly cited structured output
    2. Includes supporting_data with source citations
    3. Proposes a dummy Tier C action (for testing the approval gate)
    4. Declares confidence and caveats
    5. Reports model_used and prompt_version for reproducibility
    """
    tracer = get_tracer("agent-echo")

    with tracer.start_agent_span(
        agent_name=AGENT_ID,
        task_id="echo-task",
        tenant_id=str(task_input.tenant_id),
    ) as span:
        now = datetime.now(timezone.utc)

        # Create cited supporting data
        supporting_data = [
            SupportingDataEntry(
                source_system="mock_accounting",
                source_ref="txn_summary_2024_q4",
                value="50000",
                retrieved_at=now,
            ),
            SupportingDataEntry(
                source_system="mock_accounting",
                source_ref="runway_calculation",
                value="12",
                retrieved_at=now,
            ),
            SupportingDataEntry(
                source_system="agent_inference",
                source_ref="Trend analysis based on last 6 months of mock data",
                value="healthy",
                retrieved_at=now,
            ),
        ]

        # Create a dummy Tier C action for testing the approval gate
        suggested_actions = [
            SuggestedAction(
                action_type="schedule_meeting",
                payload={
                    "target_system": "google_calendar",
                    "title": "Q4 Review Meeting",
                    "attendees": ["founder@example.com", "advisor@example.com"],
                    "proposed_time": "2024-12-15T10:00:00Z",
                    "duration_minutes": 60,
                },
                risk_tier=RiskTier.C,  # Will be validated by platform
                rationale="Based on the financial review, a Q4 review meeting with the advisor would help discuss the $50,000 monthly burn and 12 months runway outlook.",
            ),
        ]

        output = AgentOutput(
            answer=(
                f"Echo Agent Report for tenant {task_input.tenant_id}:\n\n"
                f"Task: {task_input.task_description}\n\n"
                f"Based on mock accounting data, the monthly burn rate is $50,000 "
                f"with 12 months of runway remaining. "
                f"The overall financial health assessment is healthy based on trend analysis.\n\n"
                f"Recommendation: Schedule a Q4 review meeting to discuss these figures."
            ),
            supporting_data=supporting_data,
            confidence=ConfidenceLevel.HIGH,
            caveats=[
                "This is mock data from the Phase 0 echo agent — not real financial data.",
                "No real integrations are connected in Phase 0.",
            ],
            suggested_actions=suggested_actions,
            model_used=MODEL_USED,
            prompt_version=PROMPT_VERSION,
        )

        # Log model call for observability
        span.log_model_call(
            model_id=MODEL_USED,
            prompt_version=PROMPT_VERSION,
            prompt_tokens=100,
            completion_tokens=200,
            latency_ms=50,
        )
        span.log_confidence(output.confidence.value)

        return output


async def process_task_ungrounded(task_input: AgentInput) -> AgentOutput:
    """
    Variant that produces UNGROUNDED output — for testing grounding rejection.
    This output should be caught and rejected by the grounding validator.
    """
    return AgentOutput(
        answer=(
            "The burn rate is $75,000 per month with only 6 months of runway. "
            "Revenue grew 30% this quarter."
        ),
        supporting_data=[],  # NO citations — this should fail grounding
        confidence=ConfidenceLevel.MEDIUM,
        caveats=[],
        model_used=MODEL_USED,
        prompt_version=PROMPT_VERSION,
    )
