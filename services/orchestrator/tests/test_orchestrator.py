"""
Tests for Orchestrator, Dispatcher, and Model Router
Implements: Testing Strategy §1 (state machine), §4 (model routing)
"""

import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'packages', 'shared-types', 'python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from chief_types.models import (
    AgentInput, AgentOutput, ConfidenceLevel, GoalStatus, GoalType,
    RiskTier, SuggestedAction, SupportingDataEntry, TaskStatus,
)
from chief_types.observability import reset_tracer

from orchestrator import Orchestrator, Goal, Task, GoalClassifier
from dispatcher import Dispatcher, DispatchResult
from model_router import ModelRouter, ModelTier


TENANT_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
USER_ID = "b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22"


@pytest.fixture(autouse=True)
def reset():
    reset_tracer()


def _make_echo_output() -> AgentOutput:
    from datetime import datetime, timezone
    return AgentOutput(
        answer="Test answer with $50,000 burn rate.",
        supporting_data=[
            SupportingDataEntry(
                source_system="mock_accounting",
                source_ref="txn_summary",
                value="50000",
                retrieved_at=datetime.now(timezone.utc),
            ),
        ],
        confidence=ConfidenceLevel.HIGH,
        caveats=["Test caveat"],
        model_used="test-model",
        prompt_version="1.0.0",
    )


# ============================================================================
# State Machine Tests (AIDD §3)
# ============================================================================

class TestGoalStateMachine:
    """Test valid and invalid state transitions."""

    def test_valid_happy_path(self):
        goal = Goal(tenant_id=TENANT_ID, user_id=USER_ID, raw_text="Test")
        goal.transition(GoalStatus.CLASSIFYING)
        goal.transition(GoalStatus.DECOMPOSING)
        goal.transition(GoalStatus.DISPATCHING)
        goal.transition(GoalStatus.AWAITING_SPECIALIST_OUTPUT)
        goal.transition(GoalStatus.SYNTHESIZING)
        goal.transition(GoalStatus.DELIVERED)
        assert goal.status == GoalStatus.DELIVERED

    def test_clarification_path(self):
        goal = Goal(tenant_id=TENANT_ID, user_id=USER_ID, raw_text="Test")
        goal.transition(GoalStatus.CLASSIFYING)
        goal.transition(GoalStatus.AWAITING_CLARIFICATION)
        goal.transition(GoalStatus.DECOMPOSING)  # After clarification provided
        assert goal.status == GoalStatus.DECOMPOSING

    def test_stalled_path(self):
        goal = Goal(tenant_id=TENANT_ID, user_id=USER_ID, raw_text="Test")
        goal.transition(GoalStatus.CLASSIFYING)
        goal.transition(GoalStatus.AWAITING_CLARIFICATION)
        goal.transition(GoalStatus.STALLED)  # After 24h timeout
        assert goal.status == GoalStatus.STALLED

    def test_invalid_transition_raises(self):
        goal = Goal(tenant_id=TENANT_ID, user_id=USER_ID, raw_text="Test")
        with pytest.raises(ValueError, match="Invalid transition"):
            goal.transition(GoalStatus.DELIVERED)  # Can't go RECEIVED → DELIVERED

    def test_cannot_skip_classification(self):
        goal = Goal(tenant_id=TENANT_ID, user_id=USER_ID, raw_text="Test")
        with pytest.raises(ValueError):
            goal.transition(GoalStatus.DECOMPOSING)  # Must classify first


# ============================================================================
# Goal Classifier Tests
# ============================================================================

class TestGoalClassifier:

    def test_reporting_goal(self):
        classifier = GoalClassifier()
        goal_type, confidence = classifier.classify("Give me a financial overview report")
        assert goal_type == GoalType.REPORTING
        assert confidence > 0.7

    def test_forecast_goal(self):
        classifier = GoalClassifier()
        goal_type, confidence = classifier.classify("Forecast our runway for next 12 months")
        assert goal_type == GoalType.FORECASTING
        assert confidence > 0.7

    def test_ambiguous_goal_low_confidence(self):
        classifier = GoalClassifier()
        goal_type, confidence = classifier.classify("hmm maybe do something")
        assert confidence < 0.7  # Should trigger clarification


# ============================================================================
# Dispatcher Tests
# ============================================================================

class TestDispatcher:

    @pytest.mark.asyncio
    async def test_parallel_independent_tasks(self):
        """Independent tasks run in parallel."""
        dispatcher = Dispatcher()

        tasks = [
            Task(goal_id="g1", tenant_id=TENANT_ID, assigned_agent="AGT-A", description="Task 1"),
            Task(goal_id="g1", tenant_id=TENANT_ID, assigned_agent="AGT-B", description="Task 2"),
            Task(goal_id="g1", tenant_id=TENANT_ID, assigned_agent="AGT-C", description="Task 3"),
        ]

        call_order = []
        async def mock_agent(task):
            call_order.append(task.assigned_agent)
            return _make_echo_output()

        result = await dispatcher.dispatch_all(tasks, mock_agent)
        assert result.all_succeeded
        assert len(result.completed) == 3

    @pytest.mark.asyncio
    async def test_sequential_dependent_tasks(self):
        """Dependent tasks run after their prerequisites."""
        dispatcher = Dispatcher()

        t1 = Task(goal_id="g1", tenant_id=TENANT_ID, assigned_agent="AGT-A", description="Task 1")
        t2 = Task(goal_id="g1", tenant_id=TENANT_ID, assigned_agent="AGT-B", description="Task 2", depends_on=[t1.id])

        execution_order = []
        async def mock_agent(task):
            execution_order.append(task.assigned_agent)
            return _make_echo_output()

        result = await dispatcher.dispatch_all([t1, t2], mock_agent)
        assert result.all_succeeded
        assert execution_order == ["AGT-A", "AGT-B"]

    @pytest.mark.asyncio
    async def test_timeout_enforcement(self):
        """Tasks that exceed timeout are marked as timed out."""
        dispatcher = Dispatcher()

        task = Task(goal_id="g1", tenant_id=TENANT_ID, assigned_agent="AGT-A", description="Slow task")
        task.timeout_ms = 100  # 100ms timeout

        async def slow_agent(task):
            await asyncio.sleep(1)  # 1 second — exceeds 100ms timeout
            return _make_echo_output()

        result = await dispatcher.dispatch_all([task], slow_agent)
        assert not result.all_succeeded
        assert len(result.timed_out) == 1

    @pytest.mark.asyncio
    async def test_agent_failure_captured(self):
        """Agent exceptions are captured, not propagated."""
        dispatcher = Dispatcher()

        task = Task(goal_id="g1", tenant_id=TENANT_ID, assigned_agent="AGT-A", description="Failing task")

        async def failing_agent(task):
            raise RuntimeError("Agent crashed")

        result = await dispatcher.dispatch_all([task], failing_agent)
        assert not result.all_succeeded
        assert task.id in result.failed
        assert "crashed" in result.failed[task.id]


# ============================================================================
# Model Router Tests
# ============================================================================

class TestModelRouter:

    def test_frontier_selected_for_complex_tasks(self):
        router = ModelRouter()
        config = router.select_model("Synthesize agent outputs and analyze conflicts")
        assert config.tier == ModelTier.FRONTIER

    def test_standard_selected_for_simple_tasks(self):
        router = ModelRouter()
        config = router.select_model("Classify this goal type")
        assert config.tier == ModelTier.STANDARD

    def test_default_is_standard(self):
        router = ModelRouter()
        config = router.select_model("Some unknown task type")
        assert config.tier == ModelTier.STANDARD  # Cost-efficient default

    def test_force_tier_overrides(self):
        router = ModelRouter()
        config = router.select_model("Classify this", force_tier=ModelTier.FRONTIER)
        assert config.tier == ModelTier.FRONTIER

    @pytest.mark.asyncio
    async def test_mock_model_call(self):
        router = ModelRouter()
        result = await router.call_model(
            prompt="Test prompt",
            task_description="Classify this goal",
        )
        assert result.model_id is not None
        assert result.prompt_tokens > 0
        assert result.cost_estimate >= 0

    @pytest.mark.asyncio
    async def test_cost_tracking(self):
        router = ModelRouter()
        await router.call_model("Prompt 1", "Classify this")
        await router.call_model("Prompt 2", "Synthesize these outputs")

        summary = router.get_cost_summary()
        assert summary["total_calls"] == 2
        assert summary["total_cost_usd"] > 0


# ============================================================================
# Orchestrator Full Flow Tests
# ============================================================================

class TestOrchestratorFlow:

    @pytest.mark.asyncio
    async def test_full_happy_path(self):
        orch = Orchestrator(available_agents=["AGT-ECHO"])

        async def echo_dispatch(task):
            return _make_echo_output()

        orch.set_agent_dispatcher(echo_dispatch)

        result = await orch.process_goal(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            raw_text="Give me a financial overview report",
        )

        assert result["status"] == "delivered"
        assert result["report"] is not None
        assert result["report"]["overall_confidence"] in ("low", "medium", "high")

    @pytest.mark.asyncio
    async def test_ambiguous_goal_asks_clarification(self):
        orch = Orchestrator()
        result = await orch.process_goal(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            raw_text="hmm yeah maybe",
        )
        assert result["status"] == "awaiting_clarification"

    @pytest.mark.asyncio
    async def test_all_agents_fail_returns_failed(self):
        orch = Orchestrator(available_agents=["AGT-ECHO"])

        async def failing_dispatch(task):
            raise RuntimeError("Agent unavailable")

        orch.set_agent_dispatcher(failing_dispatch)

        result = await orch.process_goal(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            raw_text="Give me a financial report",
        )
        assert result["status"] == "failed"
