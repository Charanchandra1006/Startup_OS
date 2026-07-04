"""
Chief AI Startup OS — Observability Layer
Implements: SAD §2 (Observability), TRD §8, Deployment Guide §4

Built BEFORE agents exist so every subsequent component emits traces.
Every service initializes tracing via this module.

Capabilities:
- Distributed tracing (OpenTelemetry)
- Model call logging (prompt version, model, tokens, latency)
- Request correlation (trace_id propagation)
- Eval pipeline hooks (structured logging for grounding test results)
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator

# OpenTelemetry imports — these are the actual tracing infrastructure
# In production, these wire to Jaeger/cloud-native exporters
# For dev/test, we use in-memory or console exporters

logger = logging.getLogger("chief.observability")


class TraceContext:
    """Represents a trace span with Chief-specific attributes."""

    def __init__(
        self,
        trace_id: str,
        span_name: str,
        service_name: str,
        tenant_id: str | None = None,
        parent_span_id: str | None = None,
    ):
        self.trace_id = trace_id
        self.span_name = span_name
        self.service_name = service_name
        self.tenant_id = tenant_id
        self.parent_span_id = parent_span_id
        self.span_id = f"span_{id(self)}"
        self.attributes: dict[str, Any] = {}
        self.events: list[dict[str, Any]] = []
        self.start_time = datetime.utcnow()
        self.end_time: datetime | None = None
        self.status: str = "OK"

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.events.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {},
        })

    def set_status(self, status: str, description: str = "") -> None:
        self.status = status
        if description:
            self.attributes["status_description"] = description

    def end(self) -> None:
        self.end_time = datetime.utcnow()


class AgentRunSpan(TraceContext):
    """
    Specialized span for AI agent invocations.
    Captures model-specific attributes for the observability layer.
    """

    def __init__(
        self,
        trace_id: str,
        agent_name: str,
        task_id: str,
        tenant_id: str,
        **kwargs: Any,
    ):
        super().__init__(
            trace_id=trace_id,
            span_name=f"agent_run.{agent_name}",
            service_name=f"agent-{agent_name.lower()}",
            tenant_id=tenant_id,
            **kwargs,
        )
        self.set_attribute("agent.name", agent_name)
        self.set_attribute("agent.task_id", task_id)
        self.set_attribute("agent.tenant_id", tenant_id)

    def log_model_call(
        self,
        model_id: str,
        prompt_version: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
    ) -> None:
        """Log an AI model call with all required observability attributes."""
        self.set_attribute("ai.model_id", model_id)
        self.set_attribute("ai.prompt_version", prompt_version)
        self.set_attribute("ai.prompt_tokens", prompt_tokens)
        self.set_attribute("ai.completion_tokens", completion_tokens)
        self.set_attribute("ai.total_tokens", prompt_tokens + completion_tokens)
        self.set_attribute("ai.latency_ms", latency_ms)
        self.add_event("model_call", {
            "model": model_id,
            "prompt_version": prompt_version,
            "tokens": prompt_tokens + completion_tokens,
            "latency_ms": latency_ms,
        })

    def log_grounding_result(
        self,
        is_valid: bool,
        total_claims: int,
        grounded_claims: int,
        stripped_claims: int,
    ) -> None:
        """Log grounding validation result for the eval pipeline."""
        self.set_attribute("grounding.valid", is_valid)
        self.set_attribute("grounding.total_claims", total_claims)
        self.set_attribute("grounding.grounded_claims", grounded_claims)
        self.set_attribute("grounding.stripped_claims", stripped_claims)
        self.add_event("grounding_validation", {
            "valid": is_valid,
            "total": total_claims,
            "grounded": grounded_claims,
            "stripped": stripped_claims,
        })

    def log_confidence(self, confidence: str) -> None:
        """Log the agent's stated confidence level."""
        self.set_attribute("agent.confidence", confidence)


class TracingManager:
    """
    Manages distributed tracing across all Chief services.
    In production, this wraps OpenTelemetry SDK.
    For Phase 0, we use a lightweight in-memory implementation
    that can be swapped for OTel without changing calling code.
    """

    def __init__(self, service_name: str | None = None):
        self.service_name = service_name or os.getenv("OTEL_SERVICE_NAME", "chief")
        self._spans: list[TraceContext] = []
        self._active_spans: dict[str, TraceContext] = {}
        logger.info(f"TracingManager initialized for service: {self.service_name}")

    @contextmanager
    def start_span(
        self,
        name: str,
        trace_id: str | None = None,
        tenant_id: str | None = None,
        parent_span_id: str | None = None,
    ) -> Generator[TraceContext, None, None]:
        """Start a new trace span."""
        import uuid
        tid = trace_id or str(uuid.uuid4())
        span = TraceContext(
            trace_id=tid,
            span_name=name,
            service_name=self.service_name,
            tenant_id=tenant_id,
            parent_span_id=parent_span_id,
        )
        self._active_spans[span.span_id] = span
        try:
            yield span
        except Exception as e:
            span.set_status("ERROR", str(e))
            raise
        finally:
            span.end()
            self._spans.append(span)
            self._active_spans.pop(span.span_id, None)

    @contextmanager
    def start_agent_span(
        self,
        agent_name: str,
        task_id: str,
        tenant_id: str,
        trace_id: str | None = None,
    ) -> Generator[AgentRunSpan, None, None]:
        """Start a specialized agent run span."""
        import uuid
        tid = trace_id or str(uuid.uuid4())
        span = AgentRunSpan(
            trace_id=tid,
            agent_name=agent_name,
            task_id=task_id,
            tenant_id=tenant_id,
        )
        self._active_spans[span.span_id] = span
        try:
            yield span
        except Exception as e:
            span.set_status("ERROR", str(e))
            raise
        finally:
            span.end()
            self._spans.append(span)
            self._active_spans.pop(span.span_id, None)

    def get_trace(self, trace_id: str) -> list[TraceContext]:
        """Retrieve all spans for a given trace_id."""
        return [s for s in self._spans if s.trace_id == trace_id]

    def get_all_spans(self) -> list[TraceContext]:
        """Get all recorded spans (for testing/debugging)."""
        return list(self._spans)


# Global tracing manager instance
_tracing_manager: TracingManager | None = None


def get_tracer(service_name: str | None = None) -> TracingManager:
    """Get or create the global tracing manager."""
    global _tracing_manager
    if _tracing_manager is None:
        _tracing_manager = TracingManager(service_name)
    return _tracing_manager


def reset_tracer() -> None:
    """Reset the global tracing manager (for testing)."""
    global _tracing_manager
    _tracing_manager = None
