"""
Chief AI Startup OS — Orchestrator State Machine
Implements: AIDD §3 (state machine), WDD §1 (core goal-processing workflow)

The orchestrator owns goal decomposition, routing, and synthesis of
specialist agent output. It is the single accountable synthesis point
in the system (PVD §6.1).

State transitions:
RECEIVED → CLASSIFYING → [AWAITING_CLARIFICATION] → DECOMPOSING →
DISPATCHING → AWAITING_SPECIALIST_OUTPUT → SYNTHESIZING →
[ROUTING_ACTIONS] → DELIVERED | STALLED | FAILED
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from chief_types.models import (
    AgentInput,
    AgentOutput,
    ConfidenceLevel,
    GoalStatus,
    GoalType,
    RiskTier,
    SuggestedAction,
    TaskStatus,
)
from chief_types.grounding_validator import validate_grounding
from chief_types.observability import get_tracer

logger = logging.getLogger("chief.orchestrator")


class Goal:
    """Internal goal representation tracking state machine progression."""

    def __init__(
        self,
        tenant_id: str,
        user_id: str,
        raw_text: str,
    ):
        self.id = str(uuid.uuid4())
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.raw_text = raw_text
        self.status = GoalStatus.RECEIVED
        self.classified_type: GoalType | None = None
        self.classification_confidence: float | None = None
        self.tasks: list[Task] = []
        self.agent_outputs: dict[str, AgentOutput] = {}  # task_id → output
        self.synthesized_report: dict[str, Any] | None = None
        self.suggested_actions: list[SuggestedAction] = []
        self.conflicts_detected: bool = False
        self.conflict_detail: list[dict[str, Any]] = []
        self.trace_id = str(uuid.uuid4())
        self.created_at = datetime.now(timezone.utc)
        self.error: str | None = None

    def transition(self, new_status: GoalStatus) -> None:
        """Validate and apply a state transition."""
        valid_transitions = {
            GoalStatus.RECEIVED: {GoalStatus.CLASSIFYING, GoalStatus.FAILED},
            GoalStatus.CLASSIFYING: {
                GoalStatus.AWAITING_CLARIFICATION,
                GoalStatus.DECOMPOSING,
                GoalStatus.FAILED,
            },
            GoalStatus.AWAITING_CLARIFICATION: {
                GoalStatus.CLASSIFYING,
                GoalStatus.DECOMPOSING,
                GoalStatus.STALLED,
            },
            GoalStatus.DECOMPOSING: {GoalStatus.DISPATCHING, GoalStatus.FAILED},
            GoalStatus.DISPATCHING: {
                GoalStatus.AWAITING_SPECIALIST_OUTPUT,
                GoalStatus.FAILED,
            },
            GoalStatus.AWAITING_SPECIALIST_OUTPUT: {
                GoalStatus.SYNTHESIZING,
                GoalStatus.FAILED,
            },
            GoalStatus.SYNTHESIZING: {
                GoalStatus.ROUTING_ACTIONS,
                GoalStatus.DELIVERED,
                GoalStatus.FAILED,
            },
            GoalStatus.ROUTING_ACTIONS: {GoalStatus.DELIVERED, GoalStatus.FAILED},
        }

        allowed = valid_transitions.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition: {self.status.value} → {new_status.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        logger.info(f"Goal {self.id}: {self.status.value} → {new_status.value}")
        self.status = new_status


class Task:
    """A decomposed sub-task assigned to a specialist agent."""

    def __init__(
        self,
        goal_id: str,
        tenant_id: str,
        assigned_agent: str,
        description: str,
        depends_on: list[str] | None = None,
    ):
        self.id = str(uuid.uuid4())
        self.goal_id = goal_id
        self.tenant_id = tenant_id
        self.assigned_agent = assigned_agent
        self.description = description
        self.depends_on = depends_on or []
        self.status = TaskStatus.PENDING
        self.output: AgentOutput | None = None
        self.error: str | None = None
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None


class GoalClassifier:
    """
    Classifies goal type from natural language input.
    AIDD §3: If confidence < threshold, routes to clarification.
    """

    DEFAULT_CONFIDENCE_THRESHOLD = 0.7

    def classify(
        self,
        raw_text: str,
        confidence_threshold: float | None = None,
    ) -> tuple[GoalType, float]:
        """
        Classify a goal's type. In production, this calls the Model Router.
        Phase 0: rule-based classification for testing the pipeline.

        Returns:
            Tuple of (GoalType, confidence_score)
        """
        text_lower = raw_text.lower()

        # Simple keyword-based classification for Phase 0
        if any(kw in text_lower for kw in ["report", "summarize", "overview", "status"]):
            return GoalType.REPORTING, 0.85

        if any(kw in text_lower for kw in ["monitor", "watch", "alert", "track"]):
            return GoalType.MONITORING, 0.80

        if any(kw in text_lower for kw in ["forecast", "predict", "project", "runway"]):
            return GoalType.FORECASTING, 0.82

        if any(kw in text_lower for kw in ["board", "meeting", "deck", "prepare"]):
            return GoalType.COMPOSITE, 0.78

        if any(kw in text_lower for kw in ["send", "publish", "schedule", "create"]):
            return GoalType.ACTION_REQUEST, 0.75

        if "?" in raw_text:
            return GoalType.AD_HOC_QUESTION, 0.70

        return GoalType.UNCLASSIFIED, 0.40


class TaskDecomposer:
    """
    Decomposes a classified goal into a task graph.
    PRD FR-1.4: Task list shown to founder before execution begins.
    """

    def decompose(
        self,
        goal: Goal,
        available_agents: list[str] | None = None,
    ) -> list[Task]:
        """
        Decompose a goal into tasks for specialist agents.
        Phase 0: simple mapping based on goal type.
        Production: LLM-powered decomposition.
        """
        agents = available_agents or ["AGT-ECHO"]

        tasks = []
        if goal.classified_type == GoalType.REPORTING:
            tasks.append(Task(
                goal_id=goal.id,
                tenant_id=goal.tenant_id,
                assigned_agent=agents[0],
                description=f"Generate report for: {goal.raw_text}",
            ))

        elif goal.classified_type == GoalType.COMPOSITE:
            # Composite goals may generate multiple tasks
            for i, agent in enumerate(agents):
                tasks.append(Task(
                    goal_id=goal.id,
                    tenant_id=goal.tenant_id,
                    assigned_agent=agent,
                    description=f"Sub-task {i+1} for: {goal.raw_text}",
                ))

        else:
            # Default: single task to the first available agent
            tasks.append(Task(
                goal_id=goal.id,
                tenant_id=goal.tenant_id,
                assigned_agent=agents[0],
                description=f"Process goal: {goal.raw_text}",
            ))

        return tasks


class ConflictDetector:
    """
    Detects conflicts between specialist agent outputs.
    AIDD §6: Phase 1 scope is surface-only (no arbitration).
    """

    def detect_conflicts(
        self,
        outputs: dict[str, AgentOutput],
    ) -> tuple[bool, list[dict[str, Any]]]:
        """
        Pairwise comparison of agent outputs for contradictions.
        Returns (conflicts_detected, conflict_details).
        """
        conflicts = []
        agent_ids = list(outputs.keys())

        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                agent_a = agent_ids[i]
                agent_b = agent_ids[j]
                output_a = outputs[agent_a]
                output_b = outputs[agent_b]

                # Check for conflicting suggested actions
                if output_a.suggested_actions and output_b.suggested_actions:
                    for action_a in output_a.suggested_actions:
                        for action_b in output_b.suggested_actions:
                            if (
                                action_a.action_type == action_b.action_type
                                and action_a.payload != action_b.payload
                            ):
                                conflicts.append({
                                    "type": "conflicting_actions",
                                    "agent_a": agent_a,
                                    "agent_b": agent_b,
                                    "action_type": action_a.action_type,
                                    "detail": "Same action type with different payloads",
                                })

        return len(conflicts) > 0, conflicts


class Synthesizer:
    """
    Combines specialist outputs into a founder-facing report.
    AIDD §6: confidence-weighted, conflicts surfaced not arbitrated (Phase 1).
    """

    def synthesize(
        self,
        goal: Goal,
        outputs: dict[str, AgentOutput],
        conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Synthesize specialist outputs into a unified report.
        GR-06: Confidence may never be silently upgraded during synthesis.
        """
        # Determine overall confidence (GR-06: min of contributing outputs)
        confidences = [o.confidence for o in outputs.values()]
        confidence_order = {
            ConfidenceLevel.LOW: 0,
            ConfidenceLevel.MEDIUM: 1,
            ConfidenceLevel.HIGH: 2,
        }
        min_confidence = min(confidences, key=lambda c: confidence_order[c])

        # Collect all supporting data
        all_supporting_data = []
        for output in outputs.values():
            all_supporting_data.extend(
                [sd.model_dump() for sd in output.supporting_data]
            )

        # Collect all caveats
        all_caveats = []
        for agent_id, output in outputs.items():
            for caveat in output.caveats:
                all_caveats.append(f"[{agent_id}] {caveat}")

        # Build synthesized report
        report = {
            "goal_id": goal.id,
            "goal_text": goal.raw_text,
            "contributing_agents": list(outputs.keys()),
            "synthesized_answer": "\n\n".join(
                f"**{agent_id}**: {output.answer}"
                for agent_id, output in outputs.items()
            ),
            "supporting_data": all_supporting_data,
            "overall_confidence": min_confidence.value,
            "caveats": all_caveats,
            "conflicts_detected": len(conflicts) > 0,
            "conflicts": conflicts,
            "suggested_actions": [],
        }

        # Collect all suggested actions
        for output in outputs.values():
            report["suggested_actions"].extend(
                [a.model_dump() for a in output.suggested_actions]
            )

        if conflicts:
            report["conflict_note"] = (
                "The following recommendations are in tension — "
                "see reasoning below for each agent's position. "
                "Phase 1: the founder decides; the system surfaces but does not arbitrate."
            )

        return report


class Orchestrator:
    """
    The Orchestrator — central coordination engine.

    Owns: goal intake, classification, task decomposition, dispatch,
    synthesis, and action routing.

    Does NOT: execute actions directly, hold write credentials, or
    access data directly (only through specialist dispatch).
    """

    def __init__(
        self,
        classifier: GoalClassifier | None = None,
        decomposer: TaskDecomposer | None = None,
        conflict_detector: ConflictDetector | None = None,
        synthesizer: Synthesizer | None = None,
        available_agents: list[str] | None = None,
    ):
        self.classifier = classifier or GoalClassifier()
        self.decomposer = decomposer or TaskDecomposer()
        self.conflict_detector = conflict_detector or ConflictDetector()
        self.synthesizer = synthesizer or Synthesizer()
        self.available_agents = available_agents or ["AGT-ECHO"]
        self.tracer = get_tracer("orchestrator")
        self._goals: dict[str, Goal] = {}
        self._agent_dispatch_fn: Any = None  # Set by caller to dispatch to real agents

    def set_agent_dispatcher(self, fn: Any) -> None:
        """Set the function used to dispatch tasks to specialist agents."""
        self._agent_dispatch_fn = fn

    async def process_goal(
        self,
        tenant_id: str,
        user_id: str,
        raw_text: str,
    ) -> dict[str, Any]:
        """
        Process a founder's goal through the full state machine.
        WDD §1: The core goal-processing workflow.
        """
        with self.tracer.start_span(
            "orchestrator.process_goal",
            tenant_id=tenant_id,
        ) as span:
            # Step 1: Create goal (persist before processing — PRD FR-1.1)
            goal = Goal(tenant_id=tenant_id, user_id=user_id, raw_text=raw_text)
            goal.trace_id = span.trace_id
            self._goals[goal.id] = goal
            span.set_attribute("goal.id", goal.id)

            try:
                # Step 2: Classify
                goal.transition(GoalStatus.CLASSIFYING)
                goal_type, confidence = self.classifier.classify(raw_text)
                goal.classified_type = goal_type
                goal.classification_confidence = confidence
                span.set_attribute("goal.type", goal_type.value)
                span.set_attribute("goal.classification_confidence", confidence)

                # Check if clarification needed (AIDD §3)
                if confidence < GoalClassifier.DEFAULT_CONFIDENCE_THRESHOLD:
                    goal.transition(GoalStatus.AWAITING_CLARIFICATION)
                    span.add_event("awaiting_clarification", {
                        "confidence": confidence,
                        "threshold": GoalClassifier.DEFAULT_CONFIDENCE_THRESHOLD,
                    })
                    return {
                        "status": "awaiting_clarification",
                        "goal_id": goal.id,
                        "classified_type": goal_type.value,
                        "confidence": confidence,
                        "message": "Goal interpretation is ambiguous. Please clarify.",
                    }

                # Step 3: Decompose
                goal.transition(GoalStatus.DECOMPOSING)
                tasks = self.decomposer.decompose(goal, self.available_agents)
                goal.tasks = tasks
                span.set_attribute("goal.task_count", len(tasks))

                # Step 4: Dispatch
                goal.transition(GoalStatus.DISPATCHING)
                goal.transition(GoalStatus.AWAITING_SPECIALIST_OUTPUT)

                # Dispatch tasks to agents
                for task in tasks:
                    task.status = TaskStatus.DISPATCHED
                    task.started_at = datetime.now(timezone.utc)

                    if self._agent_dispatch_fn:
                        try:
                            output = await self._agent_dispatch_fn(task)
                            # Validate grounding before accepting output
                            grounding_result = validate_grounding(output)
                            if grounding_result.validated_output:
                                goal.agent_outputs[task.id] = grounding_result.validated_output
                            task.output = grounding_result.validated_output
                            task.status = TaskStatus.COMPLETED

                            span.add_event("task_completed", {
                                "task_id": task.id,
                                "agent": task.assigned_agent,
                                "grounding_valid": grounding_result.is_valid,
                            })
                        except Exception as e:
                            task.status = TaskStatus.FAILED
                            task.error = str(e)
                            span.add_event("task_failed", {
                                "task_id": task.id,
                                "error": str(e),
                            })
                    else:
                        task.status = TaskStatus.FAILED
                        task.error = "No agent dispatcher configured"

                    task.completed_at = datetime.now(timezone.utc)

                # Step 5: Synthesize
                goal.transition(GoalStatus.SYNTHESIZING)

                if goal.agent_outputs:
                    # Detect conflicts (AIDD §6)
                    has_conflicts, conflict_details = self.conflict_detector.detect_conflicts(
                        goal.agent_outputs
                    )
                    goal.conflicts_detected = has_conflicts
                    goal.conflict_detail = conflict_details

                    # Synthesize report
                    report = self.synthesizer.synthesize(
                        goal, goal.agent_outputs, conflict_details
                    )
                    goal.synthesized_report = report

                    # Route actions if any
                    if report.get("suggested_actions"):
                        goal.transition(GoalStatus.ROUTING_ACTIONS)
                        goal.transition(GoalStatus.DELIVERED)
                    else:
                        goal.transition(GoalStatus.DELIVERED)
                else:
                    goal.transition(GoalStatus.FAILED)
                    goal.error = "All specialist tasks failed"
                    return {
                        "status": "failed",
                        "goal_id": goal.id,
                        "error": goal.error,
                    }

                span.set_attribute("goal.final_status", goal.status.value)

                return {
                    "status": "delivered",
                    "goal_id": goal.id,
                    "trace_id": goal.trace_id,
                    "report": goal.synthesized_report,
                }

            except Exception as e:
                goal.status = GoalStatus.FAILED
                goal.error = str(e)
                span.set_status("ERROR", str(e))
                raise

    def get_goal(self, goal_id: str) -> Goal | None:
        """Retrieve a goal by ID."""
        return self._goals.get(goal_id)
