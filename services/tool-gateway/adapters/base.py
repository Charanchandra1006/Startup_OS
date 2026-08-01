"""
Chief AI Startup OS — Tool Adapter Base Interface
Implements: STARTUP_OS_MASTER_BUILD_PLAN Part 2.2

All REST and MCP adapters implement this so tool_gateway.py's dispatch
logic never needs to know which transport a provider uses.

The adapter contract:
- One instance per provider (google_workspace, quickbooks, github_mcp...)
- Instances are stateless w.r.t. tenant — all tenant state comes from the
  Vault via tenant_id, never from adapter instance attributes.
- All provider-specific exceptions MUST be caught and re-raised as one of
  the AdapterError subclasses so agents get a consistent error contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class AdapterKind(str, Enum):
    REST = "rest"
    MCP = "mcp"
    MOCK = "mock"


# ─── Error Hierarchy ─────────────────────────────────────────────────────────
# Never let raw provider exceptions (httpx.HTTPError, google.auth exceptions,
# botocore errors, etc.) leak past the adapter boundary.

class AdapterError(Exception):
    """Base class for all adapter-level failures."""


class AdapterAuthError(AdapterError):
    """Token missing, expired-and-unrefreshable, or scope insufficient."""


class AdapterRateLimitError(AdapterError):
    """Provider rate-limited us. Includes retry_after_seconds if known."""
    def __init__(self, message: str, retry_after_seconds: float | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class AdapterProviderUnavailable(AdapterError):
    """Upstream provider is down / timing out. Distinct from auth/rate-limit
    so the orchestrator can decide whether to retry, fall back, or fail the
    goal outright."""


# ─── Request / Response DTOs ─────────────────────────────────────────────────

@dataclass
class ToolExecutionRequest:
    """Immutable request object passed to every adapter.execute() call."""
    tenant_id: str
    action_type: str          # e.g. "calendar.create_event", "finance.get_transactions"
    params: dict[str, Any]
    scoped_token: str         # JWT issued by tool_gateway /tokens endpoint
    trace_id: str


@dataclass
class ToolExecutionResult:
    """Standardized result from every adapter, regardless of transport."""
    success: bool
    data: dict[str, Any] | None
    error: str | None = None
    provider_latency_ms: float | None = None


# ─── Abstract Base Adapter ───────────────────────────────────────────────────

class ToolAdapter(ABC):
    """One instance per provider (google_workspace, quickbooks, github_mcp...).

    Instances are stateless w.r.t. tenant — all tenant state comes from the
    Vault via tenant_id, never from adapter instance attributes.

    Subclasses MUST set:
    - kind: AdapterKind
    - provider_name: str
    - supported_actions: frozenset[str]
    """

    kind: AdapterKind
    provider_name: str
    supported_actions: frozenset[str]

    @abstractmethod
    async def authenticate(self, tenant_id: str) -> dict[str, Any]:
        """Return current valid credentials for this tenant, refreshing via
        the Vault-stored refresh token if the access token is expired.

        Raises AdapterAuthError if no valid credentials exist (tenant must
        re-connect this provider).
        """

    @abstractmethod
    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Perform the action. Must internally call authenticate() first.

        Must catch all provider-specific exceptions and re-raise as one of:
        - AdapterAuthError (token issues)
        - AdapterRateLimitError (429s)
        - AdapterProviderUnavailable (5xx / timeouts)
        """

    def supports(self, action_type: str) -> bool:
        """Check if this adapter handles the given action_type."""
        return action_type in self.supported_actions
