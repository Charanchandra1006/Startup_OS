"""
Chief AI Startup OS — Model Router
Implements: AIDD §4 (model selection), TRD §1

Routes LLM calls to the appropriate model tier:
- Frontier (gpt-4o): complex reasoning, synthesis, multi-step
- Standard (gpt-4o-mini): classification, simple extraction, formatting

Model selection is driven by task complexity, not agent identity.
The router applies cost/quality trade-offs and respects token budgets.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from chief_types.observability import get_tracer
from chief_types.llm_client import LLMClient

logger = logging.getLogger("chief.orchestrator.router")


class ModelTier(str, Enum):
    ORCHESTRATOR = "orchestrator"           # Gemini 2.5 Pro
    COMPLEX_REASONING = "complex_reasoning" # Gemini 2.5 Pro
    ROUTINE_CONTENT = "routine_content"     # Gemini 2.5 Flash
    TOOL_EXECUTION = "tool_execution"       # GPT-4o


@dataclass
class ModelConfig:
    """Configuration for a model endpoint."""
    model_id: str
    provider: str
    tier: ModelTier
    max_tokens: int
    timeout_seconds: int
    fallback_model_id: str | None = None
    fallback_provider: str | None = None


@dataclass
class ModelCallResult:
    """Result of a model call including usage metadata."""
    content: str
    model_id: str
    provider: str
    tier: ModelTier
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    was_fallback: bool = False


# ─── Model Configurations ───────────────────────────────────────────────────

GEMINI_PRO_CONFIG = ModelConfig(
    model_id="gemini-2.5-pro",
    provider="google",
    tier=ModelTier.COMPLEX_REASONING,
    max_tokens=8192,
    timeout_seconds=120,
    fallback_model_id="gpt-4o",
    fallback_provider="openai",
)

GEMINI_FLASH_CONFIG = ModelConfig(
    model_id="gemini-2.5-flash",
    provider="google",
    tier=ModelTier.ROUTINE_CONTENT,
    max_tokens=8192,
    timeout_seconds=60,
    fallback_model_id="gpt-4o-mini",
    fallback_provider="openai",
)

GPT_4O_CONFIG = ModelConfig(
    model_id="gpt-4o",
    provider="openai",
    tier=ModelTier.TOOL_EXECUTION,
    max_tokens=4096,
    timeout_seconds=90,
    fallback_model_id="gemini-2.5-pro",
    fallback_provider="google",
)


# ─── Task Complexity Heuristics ───────────────────────────────────────────────

# Tasks that require Gemini 2.5 Pro
PRO_TASK_PATTERNS = [
    "synthesize", "analyze conflict", "finance", "legal", "strategy", "product",
    "forecast", "orchestrate", "master"
]

# Tasks suitable for Gemini 2.5 Flash
FLASH_TASK_PATTERNS = [
    "email", "hr", "documentation", "routine", "format", "summarize simple"
]

# Tasks requiring GPT-4o
TOOL_TASK_PATTERNS = [
    "strict structured output", "tool execution", "json schema strict"
]


class ModelRouter:
    """
    Routes model calls to the appropriate tier and provider based on task complexity.
    Implements automatic fallback if a provider is unavailable/rate-limited.
    """

    def __init__(self):
        self.tracer = get_tracer("model-router")
        self._call_history: list[ModelCallResult] = []
        self._llm_client = LLMClient()

    def select_model(
        self,
        task_description: str,
        force_tier: ModelTier | None = None,
    ) -> ModelConfig:
        """Select the appropriate model configuration."""
        if force_tier:
            if force_tier in (ModelTier.ORCHESTRATOR, ModelTier.COMPLEX_REASONING):
                return GEMINI_PRO_CONFIG
            elif force_tier == ModelTier.TOOL_EXECUTION:
                return GPT_4O_CONFIG
            return GEMINI_FLASH_CONFIG

        desc_lower = task_description.lower()

        for pattern in TOOL_TASK_PATTERNS:
            if pattern in desc_lower:
                logger.debug(f"GPT-4o (Tool) selected for: {task_description[:80]}")
                return GPT_4O_CONFIG

        for pattern in PRO_TASK_PATTERNS:
            if pattern in desc_lower:
                logger.debug(f"Gemini 2.5 Pro selected for: {task_description[:80]}")
                return GEMINI_PRO_CONFIG

        for pattern in FLASH_TASK_PATTERNS:
            if pattern in desc_lower:
                logger.debug(f"Gemini 2.5 Flash selected for: {task_description[:80]}")
                return GEMINI_FLASH_CONFIG

        # Default to Flash for routine tasks
        return GEMINI_FLASH_CONFIG

    async def call_model(
        self,
        prompt: str,
        task_description: str,
        system_prompt: str | None = None,
        force_tier: ModelTier | None = None,
    ) -> ModelCallResult:
        """
        Call an LLM via the model router with fallback support.
        Phase 0/1 skeleton: implements the routing logic and mock execution.
        """
        model_config = self.select_model(task_description, force_tier)

        with self.tracer.start_span("model_router.call_model") as span:
            span.set_attribute("model.id", model_config.model_id)
            span.set_attribute("model.provider", model_config.provider)
            span.set_attribute("model.tier", model_config.tier.value)

            import time
            start = time.monotonic()
            was_fallback = False
            used_model = model_config.model_id
            used_provider = model_config.provider

            try:
                # Primary Provider Call
                content, prompt_tokens, completion_tokens = await self._llm_client.generate(
                    provider=model_config.provider,
                    model_id=model_config.model_id,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=model_config.max_tokens,
                )
            except Exception as e:
                logger.warning(f"Primary model {used_model} ({used_provider}) failed: {e}. Initiating fallback...")
                
                if not model_config.fallback_provider or not model_config.fallback_model_id:
                    logger.error(f"No fallback configured for {used_model}. Raising error.")
                    raise
                
                was_fallback = True
                used_model = model_config.fallback_model_id
                used_provider = model_config.fallback_provider
                
                span.add_event("model.fallback_initiated", attributes={
                    "error": str(e),
                    "fallback.provider": used_provider,
                    "fallback.model": used_model
                })

                # Fallback Provider Call
                content, prompt_tokens, completion_tokens = await self._llm_client.generate(
                    provider=used_provider,
                    model_id=used_model,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=model_config.max_tokens,
                )
            
            elapsed_ms = int((time.monotonic() - start) * 1000)

            result = ModelCallResult(
                content=content,
                model_id=used_model,
                provider=used_provider,
                tier=model_config.tier,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=elapsed_ms,
                was_fallback=was_fallback
            )

            self._call_history.append(result)

            span.set_attribute("model.prompt_tokens", prompt_tokens)
            span.set_attribute("model.completion_tokens", completion_tokens)
            span.set_attribute("model.latency_ms", elapsed_ms)
            span.set_attribute("model.was_fallback", was_fallback)

            return result

    def get_cost_summary(self) -> dict[str, Any]:
        """Get cost summary for all model calls."""
        total_cost = sum(r.cost_estimate for r in self._call_history)
        frontier_calls = [r for r in self._call_history if r.tier == ModelTier.FRONTIER]
        standard_calls = [r for r in self._call_history if r.tier == ModelTier.STANDARD]

        return {
            "total_calls": len(self._call_history),
            "total_cost_usd": round(total_cost, 6),
            "frontier_calls": len(frontier_calls),
            "frontier_cost_usd": round(sum(r.cost_estimate for r in frontier_calls), 6),
            "standard_calls": len(standard_calls),
            "standard_cost_usd": round(sum(r.cost_estimate for r in standard_calls), 6),
            "total_prompt_tokens": sum(r.prompt_tokens for r in self._call_history),
            "total_completion_tokens": sum(r.completion_tokens for r in self._call_history),
        }
