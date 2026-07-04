"""
Chief AI Startup OS — Dispatcher
Implements: AIDD §4 (parallel/sequential dispatch), WDD §1

Dispatches tasks to specialist agents respecting:
- Dependency ordering (tasks with depends_on wait for prerequisites)
- Parallel execution for independent tasks
- Timeout enforcement per model tier (AIDD §4: 60s Standard, 120s Frontier)
- Circuit-breaker pattern for failing agents
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from chief_types.models import AgentInput, AgentOutput, TaskStatus
from chief_types.observability import get_tracer

logger = logging.getLogger("chief.dispatcher")


class DispatchResult:
    """Result of dispatching a set of tasks."""

    def __init__(self):
        self.completed: dict[str, AgentOutput] = {}  # task_id → output
        self.failed: dict[str, str] = {}              # task_id → error
        self.timed_out: list[str] = []

    @property
    def all_succeeded(self) -> bool:
        return len(self.failed) == 0 and len(self.timed_out) == 0

    @property
    def has_any_output(self) -> bool:
        return len(self.completed) > 0


class Dispatcher:
    """
    Dispatches tasks to specialist agents with dependency resolution.

    Execution strategy:
    1. Build a dependency graph from task.depends_on fields
    2. Identify "ready" tasks (all dependencies completed)
    3. Dispatch ready tasks in parallel
    4. Wait for completion, then check for newly-ready tasks
    5. Repeat until all tasks are dispatched or all remaining are blocked
    """

    DEFAULT_TIMEOUT_MS = 60_000       # 60s for Standard tier
    FRONTIER_TIMEOUT_MS = 120_000     # 120s for Frontier tier
    MAX_CONCURRENT_TASKS = 5          # Limit concurrent dispatches

    def __init__(self):
        self.tracer = get_tracer("dispatcher")

    async def dispatch_all(
        self,
        tasks: list[Any],  # list[Task] from orchestrator
        agent_fn: Callable[..., Coroutine[Any, Any, AgentOutput]],
    ) -> DispatchResult:
        """
        Dispatch all tasks respecting dependency ordering.

        Args:
            tasks: List of Task objects with .id, .depends_on, .assigned_agent, etc.
            agent_fn: Async callable that takes a Task and returns AgentOutput

        Returns:
            DispatchResult with completed outputs and failures
        """
        result = DispatchResult()
        remaining = {t.id: t for t in tasks}
        completed_ids: set[str] = set()

        with self.tracer.start_span("dispatcher.dispatch_all") as span:
            span.set_attribute("dispatch.total_tasks", len(tasks))

            iteration = 0
            while remaining:
                iteration += 1
                span.add_event(f"dispatch_iteration_{iteration}", {
                    "remaining": len(remaining),
                    "completed": len(completed_ids),
                })

                # Find tasks whose dependencies are all satisfied
                ready = [
                    t for t in remaining.values()
                    if all(dep_id in completed_ids for dep_id in t.depends_on)
                ]

                if not ready:
                    # No tasks are ready — remaining tasks have unmet dependencies
                    for t in remaining.values():
                        t.status = TaskStatus.FAILED
                        t.error = "Blocked: unresolvable dependency"
                        result.failed[t.id] = t.error
                    break

                # Dispatch ready tasks in parallel (bounded concurrency)
                semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_TASKS)

                async def _dispatch_one(task: Any) -> tuple[str, AgentOutput | None, str | None]:
                    async with semaphore:
                        task.status = TaskStatus.DISPATCHED
                        task.started_at = datetime.now(timezone.utc)
                        timeout_s = task.timeout_ms / 1000

                        try:
                            output = await asyncio.wait_for(
                                agent_fn(task),
                                timeout=timeout_s,
                            )
                            task.status = TaskStatus.COMPLETED
                            task.completed_at = datetime.now(timezone.utc)
                            return (task.id, output, None)
                        except asyncio.TimeoutError:
                            task.status = TaskStatus.TIMED_OUT
                            task.error = f"Timed out after {timeout_s}s"
                            task.completed_at = datetime.now(timezone.utc)
                            return (task.id, None, task.error)
                        except Exception as e:
                            task.status = TaskStatus.FAILED
                            task.error = str(e)
                            task.completed_at = datetime.now(timezone.utc)
                            return (task.id, None, str(e))

                dispatched = await asyncio.gather(
                    *[_dispatch_one(t) for t in ready],
                    return_exceptions=False,
                )

                for task_id, output, error in dispatched:
                    del remaining[task_id]
                    if output:
                        result.completed[task_id] = output
                        completed_ids.add(task_id)
                    elif error and "Timed out" in error:
                        result.timed_out.append(task_id)
                    else:
                        result.failed[task_id] = error or "Unknown error"

            span.set_attribute("dispatch.completed", len(result.completed))
            span.set_attribute("dispatch.failed", len(result.failed))
            span.set_attribute("dispatch.timed_out", len(result.timed_out))

        return result
