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

import os
import sys
import logging
import uuid
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
    GoalStatus,
    GoalType,
    RiskTier,
    SuggestedAction,
    TaskStatus,
)
from chief_types.grounding_validator import validate_grounding
from chief_types.observability import get_tracer
from dispatcher import Dispatcher
from model_router import ModelRouter

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
        self.timeout_ms = 120_000  # 120s default timeout
        self.output: AgentOutput | None = None
        self.error: str | None = None
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None


class GoalClassifier:
    """
    Classifies a raw text goal into a GoalType using an LLM.
    """

    DEFAULT_CONFIDENCE_THRESHOLD = 0.65

    async def classify(
        self,
        raw_text: str,
        router: Any,
    ) -> tuple[GoalType, float]:
        """
        Classify a goal's type via LLM.
        """
        import json
        
        prompt = f"""
        Classify the following goal from a startup founder into one of these categories:
        {', '.join([e.value for e in GoalType])}
        
        Goal: "{raw_text}"
        
        Return ONLY valid JSON in this exact schema, with no markdown formatting:
        {{
            "type": "<one of the categories>",
            "confidence": <float between 0.0 and 1.0>
        }}
        """
        try:
            result = await router.call_model(
                prompt=prompt,
                task_description="Classify founder goal",
            )
            content = result.content
            if content.startswith("```json"): content = content[7:-3]
            elif content.startswith("```"): content = content[3:-3]
            
            parsed = json.loads(content)
            goal_type_str = parsed.get("type", GoalType.UNCLASSIFIED.value)
            confidence = float(parsed.get("confidence", 0.4))
            
            try:
                goal_type = GoalType(goal_type_str)
            except ValueError:
                goal_type = GoalType.UNCLASSIFIED
                
            return goal_type, confidence
        except Exception as e:
            logger.error(f"Goal classification failed: {e}")
            return GoalType.UNCLASSIFIED, 0.40


class TaskDecomposer:
    """
    Decomposes a classified goal into a task graph using LLM.
    PRD FR-1.4: Task list shown to founder before execution begins.
    """

    async def decompose(
        self,
        goal: Goal,
        available_agents: list[str],
        router: Any,
    ) -> list[Task]:
        """
        Decompose a goal into tasks for specialist agents via LLM.
        """
        import json
        
        prompt = f"""
        You are decomposing a founder's goal into discrete tasks for specialist AI agents.
        
        Goal: "{goal.raw_text}"
        Goal Type: {goal.classified_type.value}
        
        Available Agents:
        {json.dumps(available_agents, indent=2)}
        
        Create a task plan. Return ONLY valid JSON in this exact schema:
        {{
            "tasks": [
                {{
                    "assigned_agent": "<agent_id>",
                    "description": "<detailed instruction for the agent>"
                }}
            ]
        }}
        """
        try:
            result = await router.call_model(
                prompt=prompt,
                task_description=f"Decompose goal: {goal.raw_text[:50]}",
            )
            content = result.content
            if content.startswith("```json"): content = content[7:-3]
            elif content.startswith("```"): content = content[3:-3]
            
            parsed = json.loads(content)
            tasks_data = parsed.get("tasks", [])
            
            tasks = []
            for t in tasks_data:
                agent = t.get("assigned_agent")
                if agent not in available_agents:
                    agent = available_agents[0] if available_agents else "AGT-ECHO"
                
                tasks.append(Task(
                    goal_id=goal.id,
                    tenant_id=goal.tenant_id,
                    assigned_agent=agent,
                    description=t.get("description", "Process task")
                ))
                
            if not tasks:
                raise ValueError("No tasks generated")
                
            return tasks
            
        except Exception as e:
            logger.error(f"Task decomposition failed: {e}")
            # Fallback
            agent = available_agents[0] if available_agents else "AGT-ECHO"
            return [Task(
                goal_id=goal.id,
                tenant_id=goal.tenant_id,
                assigned_agent=agent,
                description=f"Process goal: {goal.raw_text}"
            )]


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
    Synthesizes multiple agent outputs into a cohesive founder report using LLM.
    """

    async def synthesize(
        self,
        goal: Goal,
        outputs: dict[str, AgentOutput],
        conflicts: list[dict[str, Any]],
        router: Any,
    ) -> tuple[dict[str, Any], list[SuggestedAction]]:
        """
        Synthesize via LLM.
        """
        import json
        
        min_confidence = min(
            (out.confidence for out in outputs.values()),
            default=ConfidenceLevel.HIGH,
        )

        all_supporting_data = []
        for output in outputs.values():
            all_supporting_data.extend(
                [sd.model_dump() for sd in output.supporting_data]
            )

        all_caveats = []
        for agent_id, output in outputs.items():
            for caveat in output.caveats:
                all_caveats.append(f"[{agent_id}] {caveat}")

        # Extract actions natively
        all_actions = []
        for output in outputs.values():
            all_actions.extend(output.suggested_actions)
            
        outputs_text = json.dumps({
            agent_id: {
                "answer": out.answer,
                "confidence": out.confidence.value,
                "caveats": out.caveats
            }
            for agent_id, out in outputs.items()
        }, indent=2)

        prompt = f"""
        Synthesize the following agent outputs into a single cohesive executive report for a startup founder.
        
        Original Goal: "{goal.raw_text}"
        
        Agent Outputs:
        {outputs_text}
        
        Conflicts Detected:
        {json.dumps(conflicts, indent=2) if conflicts else "None"}
        
        Return ONLY valid JSON in this exact schema:
        {{
            "synthesized_answer": "<markdown formatted executive summary and synthesis>"
        }}
        """
        
        try:
            result = await router.call_model(
                prompt=prompt,
                task_description=f"Synthesize report for: {goal.raw_text[:50]}",
            )
            content = result.content
            if content.startswith("```json"): content = content[7:-3]
            elif content.startswith("```"): content = content[3:-3]
            
            parsed = json.loads(content)
            synthesized_answer = parsed.get("synthesized_answer", "Failed to parse synthesis.")
            
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            synthesized_answer = "\n\n".join(
                f"**{agent_id}**: {output.answer}"
                for agent_id, output in outputs.items()
            )

        report = {
            "goal_id": goal.id,
            "goal_text": goal.raw_text,
            "contributing_agents": list(outputs.keys()),
            "synthesized_answer": synthesized_answer,
            "supporting_data": all_supporting_data,
            "overall_confidence": min_confidence.value,
            "caveats": all_caveats,
            "conflicts_detected": len(conflicts) > 0,
            "conflicts": conflicts,
            "suggested_actions": [a.model_dump() for a in all_actions],
        }

        if conflicts:
            report["conflict_note"] = (
                "The following recommendations are in tension — "
                "see reasoning below for each agent's position. "
                "Phase 1: the founder decides; the system surfaces but does not arbitrate."
            )

        return report, all_actions


class Orchestrator:
    """
    The Orchestrator — central coordination engine.

    Owns: goal intake, classification, task decomposition, dispatch,
    synthesis, and action routing.

    Does NOT: execute actions directly, hold write credentials, or
    access data directly (only through specialist dispatch).
    """

    def __init__(self, db_pool=None):
        self.tracer = get_tracer("orchestrator")
        self.db_pool = db_pool
        self.classifier = GoalClassifier()
        self.decomposer = TaskDecomposer()
        self.synthesizer = Synthesizer()
        self.conflict_detector = ConflictDetector()
        self.router = ModelRouter()
        self.dispatcher = Dispatcher()
        
        # Hardcoded registry for Phase 1
        self.available_agents = {
            "AGT-FIN": "Finance Agent",
            "AGT-EA": "Executive Assistant Agent",
            "AGT-PM": "Project Management Agent",
            "AGT-SAL": "Sales Agent",
            "AGT-CS": "Customer Success Agent",
            "AGT-ANL": "Analytics Agent",
            "AGT-ECHO": "Echo Test Agent",
        }
        self._goals: dict[str, Goal] = {}
        self._agent_dispatch_fn: Any = None  # Set by caller to dispatch to real agents

    def set_agent_dispatcher(self, fn: Any) -> None:
        """Set the function used to dispatch tasks to specialist agents."""
        self._agent_dispatch_fn = fn

    async def process_goal(
        self,
        goal_id: str,
        raw_text: str,
        context: Any
    ) -> dict[str, Any]:
        """
        Process a founder's goal through the full state machine.
        WDD §1: The core goal-processing workflow.
        """
        tenant_id = context.tenant_id
        user_id = context.user_id
        with self.tracer.start_span(
            "orchestrator.process_goal",
            tenant_id=tenant_id,
        ) as span:
            # tenant_id and user_id already extracted above
            
            # Step 1: Create goal (persist before processing — PRD FR-1.1)
            goal = Goal(tenant_id=tenant_id, user_id=user_id, raw_text=raw_text)
            goal.id = goal_id # Override with passed in ID
            goal.trace_id = span.trace_id
            self._goals[goal.id] = goal
            
            # Make the goal available to the server
            self.state = goal.status
            self.final_report = None
            
            span.set_attribute("goal.id", goal.id)

            try:
                # Step 2: Classify
                goal.transition(GoalStatus.CLASSIFYING)
                self.state = goal.status
                self._update_db_status_sync(goal)
                
                goal_type, confidence = await self.classifier.classify(raw_text, self.router)
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
                self.state = goal.status
                self._update_db_status_sync(goal)
                
                tasks = await self.decomposer.decompose(goal, list(self.available_agents.keys()), self.router)
                goal.tasks = tasks
                span.set_attribute("goal.task_count", len(tasks))

                # Step 4: Dispatch
                goal.transition(GoalStatus.DISPATCHING)
                self.state = goal.status
                self._update_db_status_sync(goal)
                
                goal.transition(GoalStatus.AWAITING_SPECIALIST_OUTPUT)
                self.state = goal.status
                self._update_db_status_sync(goal)

                # Dispatch tasks to agents in parallel
                if self._agent_dispatch_fn:
                    dispatch_result = await self.dispatcher.dispatch_all(tasks, self._agent_dispatch_fn)
                    
                    for task in tasks:
                        if task.id in dispatch_result.completed:
                            output = dispatch_result.completed[task.id]
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
                        else:
                            task.status = TaskStatus.FAILED
                            task.error = dispatch_result.failed.get(task.id, "Unknown error")
                            span.add_event("task_failed", {
                                "task_id": task.id,
                                "error": task.error,
                            })
                else:
                    for task in tasks:
                        task.status = TaskStatus.FAILED
                        task.error = "No agent dispatcher configured"
                        task.completed_at = datetime.now(timezone.utc)

                # Step 5: Synthesize
                goal.transition(GoalStatus.SYNTHESIZING)
                self.state = goal.status
                self._update_db_status_sync(goal)
                
                if goal.agent_outputs:
                    # Detect conflicts (AIDD §6)
                    has_conflicts, conflict_details = self.conflict_detector.detect_conflicts(
                        goal.agent_outputs
                    )
                    goal.conflicts_detected = has_conflicts
                    goal.conflict_detail = conflict_details

                    # Synthesize report
                    final_report, actions = await self.synthesizer.synthesize(
                        goal, goal.agent_outputs, conflict_details, self.router
                    )
                    goal.synthesized_report = final_report
                    
                    self.final_report = type('ReportWrapper', (), {'dict': lambda: final_report})

                    # Step 6: Route Actions (if any)
                    if actions:
                        goal.transition(GoalStatus.ROUTING_ACTIONS)
                        self.state = goal.status
                        self._update_db_status_sync(goal)
                        
                        # Execution Service integration happens here in Phase 2
                        span.add_event("actions_routed", {"count": len(actions)})

                    # Step 7: Deliver
                    goal.transition(GoalStatus.DELIVERED)
                    self.state = goal.status
                    self._update_db_status_sync(goal)
                    
                    span.set_status("OK")
                    return {
                        "status": "delivered",
                        "goal_id": goal.id,
                        "report": final_report,
                        "actions": [a.model_dump() for a in actions],
                    }
                else:
                    goal.transition(GoalStatus.FAILED)
                    self.state = goal.status
                    self._update_db_status_sync(goal)
                    
                    goal.error = "All specialist tasks failed"
                    return {
                        "status": "failed",
                        "goal_id": goal.id,
                        "error": goal.error,
                    }

            except Exception as e:
                goal.transition(GoalStatus.FAILED)
                self.state = goal.status
                self._update_db_status_sync(goal)
                
                goal.error = str(e)
                logger.error(f"Goal {goal.id} failed: {e}", exc_info=True)
                span.set_status("ERROR", str(e))
                return {
                    "status": "failed",
                    "goal_id": goal.id,
                    "error": str(e),
                }

    def _update_db_status_sync(self, goal):
        """Helper to update DB status asynchronously without awaiting in the main flow (fire and forget for now)"""
        import asyncio
        if self.db_pool:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._do_update_db(goal))
            except RuntimeError:
                pass

    async def _do_update_db(self, goal):
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("UPDATE goals SET status = $1 WHERE id = $2", goal.status.value, uuid.UUID(goal.id))
        except Exception as e:
            logger.error(f"Failed to update goal {goal.id} status in DB: {e}")

    def get_goal(self, goal_id: str) -> Goal | None:
        """Retrieve a goal by ID."""
        return self._goals.get(goal_id)
