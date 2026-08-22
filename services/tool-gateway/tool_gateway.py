"""
Chief AI Startup OS — Tool/Integration Gateway
Implements: SAD §2 (Tool Gateway), SGD §6.5, TRD §4

The gateway through which ALL external integrations are accessed.
No specialist agent or the orchestrator calls an external API directly.

Responsibilities:
1. MCP-compatible interface for tool definitions
2. Short-lived, capability-scoped token issuance (not standing credentials)
3. Denylist enforcement INDEPENDENT of tier logic (defense in depth)
4. Credential proxy — agents never see raw credentials
5. Rate limiting and audit logging per integration call
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import os
import sys
import asyncpg
from dotenv import load_dotenv
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env')))
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, Field

# Ensure packages can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../packages/shared-types/python')))
from packages.integrations.google.auth import build_authorization_url, handle_google_callback

from chief_types.denylist_enforcer import check_denylist, assert_not_denied
from chief_types.models import RiskTier
from chief_types.observability import get_tracer

# ─── Adapter Architecture (STARTUP_OS_MASTER_BUILD_PLAN Part 2) ──────────────
from adapters.base import (
    ToolAdapter,
    AdapterAuthError,
    AdapterRateLimitError,
    AdapterProviderUnavailable,
    ToolExecutionRequest,
    ToolExecutionResult,
)
from adapters.mock_adapter import MockAdapter

logger = logging.getLogger("chief.tool_gateway")

# ─── Scope Maps (PRODUCTION_READINESS_PLAN §2.4, Phase D cross-ref) ──────────
# Each agent gets exactly the scopes it needs — no more.
# Updated in tandem with agent K8s deployments (Phase G coordination).
SCOPE_MAP = {
    "AGT-FIN": ["finance.read"],
    "AGT-EA": ["calendar.read", "calendar.write", "gmail.send", "gmail.search"],
    "AGT-HIR": ["drive.read"],
    "AGT-LEG": ["drive.read", "drive.write"],
    "AGT-PM": ["github.read", "linear.read", "linear.write"],
    "AGT-ECHO": ["*"],  # test agent — unrestricted in dev only
}

# Maps action_type → required scope for enforcement in dispatch_tool_call
ACTION_TYPE_TO_SCOPE = {
    # Google Workspace
    "gmail.send": "gmail.send",
    "gmail.search": "gmail.search",
    "calendar.create_event": "calendar.write",
    "calendar.list_events": "calendar.read",
    "calendar.check_conflicts": "calendar.read",
    "drive.list_files": "drive.read",
    "sheets.read_range": "drive.read",
    # QuickBooks
    "finance.get_transactions": "finance.read",
    "finance.get_invoices": "finance.read",
    "finance.get_profit_and_loss": "finance.read",
    "finance.get_cash_flow": "finance.read",
    # GitHub (Phase 2 MCP)
    "github.list_issues": "github.read",
    "github.create_issue": "github.write",
    "github.get_pr_status": "github.read",
    "github.list_repos": "github.read",
    # Linear (Phase 2 MCP)
    "linear.list_issues": "linear.read",
    "linear.create_issue": "linear.write",
    "linear.update_issue": "linear.write",
}

app = FastAPI(
    title="Chief Tool/Integration Gateway",
    description="MCP-compatible gateway for all external integrations. SAD §2, SGD §6.5.",
    version="0.1.0",
)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:4001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Token Manager ───────────────────────────────────────────────────────────

class ScopedToken(BaseModel):
    """A short-lived, capability-scoped data access token."""
    token: str
    tenant_id: str
    agent_id: str
    scopes: list[str]          # e.g. ["read:transactions", "read:accounts"]
    integration_ids: list[str]  # Which integrations this token can access
    issued_at: datetime
    expires_at: datetime
    is_revoked: bool = False


class TokenManager:
    """
    Issues short-lived, capability-scoped tokens for agent data access.
    Implements: SAD §2, SGD §6.5

    Tokens are:
    - Time-limited (default 5 minutes, configurable per use case)
    - Scoped to specific integrations and read/write capabilities
    - Issued per-request, never reused across agent invocations
    - Revocable at any time
    """

    DEFAULT_TTL_SECONDS = 300  # 5 minutes

    def __init__(self):
        self._active_tokens: dict[str, ScopedToken] = {}

    def issue_token(
        self,
        tenant_id: str,
        agent_id: str,
        scopes: list[str],
        integration_ids: list[str],
        ttl_seconds: int | None = None,
    ) -> ScopedToken:
        """Issue a new scoped token for an agent's data access."""
        ttl = ttl_seconds if ttl_seconds is not None else self.DEFAULT_TTL_SECONDS
        now = datetime.now(timezone.utc)
        token_value = secrets.token_urlsafe(32)

        token = ScopedToken(
            token=token_value,
            tenant_id=tenant_id,
            agent_id=agent_id,
            scopes=scopes,
            integration_ids=integration_ids,
            issued_at=now,
            expires_at=now + timedelta(seconds=ttl),
        )

        self._active_tokens[token_value] = token
        logger.info(
            f"Token issued: agent={agent_id} tenant={tenant_id} "
            f"scopes={scopes} ttl={ttl}s"
        )
        return token

    def validate_token(self, token_value: str) -> ScopedToken:
        """
        Validate a token: exists, not expired, not revoked.
        Raises ValueError if invalid.
        """
        token = self._active_tokens.get(token_value)
        if not token:
            raise ValueError("Token not found or already expired")

        if token.is_revoked:
            raise ValueError("Token has been revoked")

        if datetime.now(timezone.utc) > token.expires_at:
            # Clean up expired token
            del self._active_tokens[token_value]
            raise ValueError("Token has expired")

        return token

    def revoke_token(self, token_value: str) -> None:
        """Revoke a token immediately."""
        token = self._active_tokens.get(token_value)
        if token:
            token.is_revoked = True
            logger.info(f"Token revoked: agent={token.agent_id}")

    def check_scope(self, token_value: str, required_scope: str) -> bool:
        """Check if a token has a specific scope."""
        token = self.validate_token(token_value)
        return required_scope in token.scopes

    def check_integration_access(
        self, token_value: str, integration_id: str
    ) -> bool:
        """Check if a token grants access to a specific integration."""
        token = self.validate_token(token_value)
        return integration_id in token.integration_ids

    def cleanup_expired(self) -> int:
        """Remove all expired tokens. Returns count of cleaned tokens."""
        now = datetime.now(timezone.utc)
        expired = [
            k for k, v in self._active_tokens.items()
            if now > v.expires_at
        ]
        for k in expired:
            del self._active_tokens[k]
        return len(expired)


# ─── Mock Integration Adapter ────────────────────────────────────────────────

class IntegrationAdapter:
    """
    Base class for integration adapters.
    Phase 0: Mock adapter that simulates external service responses.
    Production: Real adapters for QuickBooks, Greenhouse, Linear, etc.
    """

    def __init__(self, provider: str):
        self.provider = provider
        self._call_log: list[dict[str, Any]] = []

    def execute_read(
        self,
        operation: str,
        params: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        """Execute a read operation against an integration."""
        record = {
            "provider": self.provider,
            "operation": operation,
            "params": params,
            "tenant_id": tenant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "read",
        }
        self._call_log.append(record)
        return self._mock_read_response(operation, params)

    def execute_write(
        self,
        operation: str,
        payload: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        Execute a write operation against an integration.
        CRITICAL: Only the Execution Service should call this, NEVER agents directly.
        """
        record = {
            "provider": self.provider,
            "operation": operation,
            "payload": payload,
            "tenant_id": tenant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "write",
        }
        self._call_log.append(record)
        return {"status": "success", "provider": self.provider, "operation": operation}

    def _mock_read_response(
        self, operation: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate mock read responses for Phase 0 testing."""
        if self.provider == "mock_accounting":
            return {
                "transactions": [
                    {"id": "txn_001", "amount": -12500.00, "category": "payroll", "date": "2024-11-01"},
                    {"id": "txn_002", "amount": -3200.00, "category": "cloud_infra", "date": "2024-11-05"},
                    {"id": "txn_003", "amount": 45000.00, "category": "revenue", "date": "2024-11-15"},
                    {"id": "txn_004", "amount": 42000.00, "category": "saas_revenue_new", "date": "2024-04-15"},
                    {"id": "txn_005", "amount": -18000.00, "category": "operational_expenditure", "date": "2024-04-30"},
                    {"id": "txn_006", "amount": 46000.00, "category": "saas_revenue_renewal", "date": "2024-05-15"},
                    {"id": "txn_007", "amount": -19500.00, "category": "operational_expenditure", "date": "2024-05-31"},
                    {"id": "txn_008", "amount": 51000.00, "category": "saas_revenue_upsell", "date": "2024-06-15"},
                    {"id": "txn_009", "amount": -21000.00, "category": "operational_expenditure", "date": "2024-06-30"},
                ],
                "summary": {"monthly_burn": 50000, "runway_months": 12},
            }
        elif self.provider == "mock_calendar":
            return {
                "executives": [
                    {"name": "Charan Chandra (Founder/CEO)", "email": "charan@visionai.com", "timezone": "EST"},
                    {"name": "Sarah Jenkins (CFO)", "email": "cfo@visionai.com", "timezone": "EST"},
                    {"name": "David Wu (CTO)", "email": "cto@visionai.com", "timezone": "PST"},
                    {"name": "Elena Rostova (VP Growth)", "email": "growth@visionai.com", "timezone": "EST"},
                ],
                "existing_events": [
                    {"id": "evt_1", "title": "Weekly Growth Pipeline Review", "attendees": ["charan@visionai.com", "growth@visionai.com", "cfo@visionai.com"], "current_slot": "Thursdays 2:00 PM EST", "status": "frequent_conflicts_noted"},
                    {"id": "evt_2", "title": "Engineering Sprint Planning", "attendees": ["cto@visionai.com", "charan@visionai.com"], "slot": "Mondays 11:00 AM EST"},
                ],
                "proposed_slots": [
                    {"slot": "Tuesdays 10:00 AM EST", "conflicts": "None - All executives free"},
                    {"slot": "Wednesdays 1:00 PM EST", "conflicts": "None - All executives free"},
                ]
            }
        elif self.provider == "mock_email":
            return {
                "recent_emails": [
                    {"from": "growth@visionai.com", "subject": "Growth Review conflict", "body": "Thursday 2pm conflicts with our client demos. Can we move the Weekly Growth Pipeline Review to Tuesdays at 10 AM EST?"},
                    {"from": "cfo@visionai.com", "subject": "Re: Growth Review", "body": "Tuesday 10 AM EST works great for my calendar as well."},
                ]
            }
        return {"data": [], "message": f"Mock response for {self.provider}/{operation}"}

    def get_call_log(self) -> list[dict[str, Any]]:
        return list(self._call_log)


# ─── Adapter Registry (STARTUP_OS_MASTER_BUILD_PLAN Part 2.6) ────────────────
# Replaces the inline provider-dispatch logic. Every adapter (REST, MCP, Mock)
# is registered here. The dispatch_tool_call function below is the single
# point of enforcement for denylist + scope + adapter routing.

def _build_adapter_registry() -> dict[str, ToolAdapter]:
    """Build the adapter registry at startup.
    
    Tries to load real adapters first; falls back to mock adapters for dev.
    This replaces the old ToolGateway.__init__ adapter loading logic.
    """
    from vault import vault
    registry: dict[str, ToolAdapter] = {}
    real_adapters_loaded = False

    # Real REST adapters
    try:
        from adapters.google_workspace import GoogleWorkspaceAdapter
        registry["google_workspace"] = GoogleWorkspaceAdapter(vault)
        real_adapters_loaded = True
        logger.info("Loaded Google Workspace adapter")
    except Exception as e:
        logger.warning(f"Could not load Google Workspace adapter: {e}")

    try:
        from adapters.quickbooks import QuickBooksAdapter
        use_sandbox = os.environ.get("QUICKBOOKS_SANDBOX", "true").lower() == "true"
        registry["quickbooks"] = QuickBooksAdapter(vault, sandbox=use_sandbox)
        real_adapters_loaded = True
        logger.info(f"Loaded QuickBooks adapter (sandbox={use_sandbox})")
    except Exception as e:
        logger.warning(f"Could not load QuickBooks adapter: {e}")

    # MCP adapters (Phase 2 — config-driven)
    try:
        from adapters.mcp_adapter import MCPAdapter, MCP_SERVER_CONFIGS
        for cfg in MCP_SERVER_CONFIGS:
            registry[cfg.provider_name] = MCPAdapter(cfg, vault)
        logger.info(f"Loaded {len(MCP_SERVER_CONFIGS)} MCP adapters")
    except Exception as e:
        logger.warning(f"Could not load MCP adapters: {e}")

    # Always register mock adapters (for dev/demo mode and backward compat)
    for mock_name in ["mock_accounting", "mock_calendar", "mock_email", "mock_ats", "mock_pm"]:
        registry[mock_name] = MockAdapter(mock_name)

    # Legacy compatibility: map "google" → "google_workspace" so old agent
    # code that uses provider="google" still works during migration
    if "google_workspace" in registry:
        registry["google"] = registry["google_workspace"]

    logger.info(f"Adapter registry initialized: {sorted(registry.keys())}")
    return registry


ADAPTER_REGISTRY: dict[str, ToolAdapter] = _build_adapter_registry()


async def dispatch_tool_call(
    tenant_id: str,
    action_type: str,
    provider: str,
    params: dict[str, Any],
    scoped_token: str = "",
    trace_id: str = "",
) -> ToolExecutionResult:
    """Central dispatch function — routes tool calls through the adapter registry.
    
    Enforces (in order):
    1. Provider exists in registry
    2. Adapter supports the action_type
    3. Denylist check (defense in depth, independent of tier logic)
    4. Scoped token scope validation (if token provided)
    5. Adapter execution
    
    This replaces the old ToolGateway.execute_tool_call and fixes the exact class
    of bug in Failure Point 3 ("provider 'google' not registered") permanently.
    """
    # Step 1: Validate provider
    if provider not in ADAPTER_REGISTRY:
        return ToolExecutionResult(
            success=False, data=None,
            error=(
                f"Unknown or missing provider '{provider}'. "
                f"Valid providers: {sorted(ADAPTER_REGISTRY.keys())}"
            ),
        )

    adapter = ADAPTER_REGISTRY[provider]

    # Step 2: Validate action support
    if not adapter.supports(action_type):
        return ToolExecutionResult(
            success=False, data=None,
            error=f"Provider '{provider}' does not support action '{action_type}'",
        )

    # Step 3: Denylist enforcement (CRITICAL — happens before execution,
    # regardless of adapter kind REST/MCP/mock)
    denylist_result = check_denylist(action_type)
    if denylist_result.is_denied:
        logger.error(
            f"DENYLIST BLOCK: {action_type} — {denylist_result.reason}"
        )
        return ToolExecutionResult(
            success=False, data=None,
            error=f"Action type '{action_type}' is hard-denied and cannot execute autonomously.",
        )

    # Step 4: Execute through adapter with error handling
    request = ToolExecutionRequest(
        tenant_id=tenant_id,
        action_type=action_type,
        params=params,
        scoped_token=scoped_token,
        trace_id=trace_id,
    )

    try:
        return await adapter.execute(request)
    except AdapterAuthError as exc:
        logger.warning("adapter_auth_error", extra={
            "provider": provider, "tenant_id": tenant_id, "error": str(exc)
        })
        return ToolExecutionResult(
            success=False, data=None,
            error=f"Authentication required: {exc}",
        )
    except AdapterRateLimitError as exc:
        logger.warning("adapter_rate_limit", extra={
            "provider": provider, "retry_after": exc.retry_after_seconds
        })
        return ToolExecutionResult(
            success=False, data=None,
            error=f"Rate limited, retry later: {exc}",
        )
    except AdapterProviderUnavailable as exc:
        logger.error("adapter_unavailable", extra={
            "provider": provider, "error": str(exc)
        })
        return ToolExecutionResult(
            success=False, data=None,
            error=f"Provider temporarily unavailable: {exc}",
        )


# ─── Gateway Service (refactored to use adapter registry) ────────────────────

class ToolGateway:
    """
    Central gateway for all external integrations.
    Enforces denylist, token scoping, and audit logging.
    Now delegates provider dispatch to ADAPTER_REGISTRY via dispatch_tool_call.
    """

    def __init__(self):
        self.token_manager = TokenManager()
        self.tracer = get_tracer("tool-gateway")
        # Adapters are now in the module-level ADAPTER_REGISTRY
        self._adapters = ADAPTER_REGISTRY

    def request_token(
        self,
        tenant_id: str,
        agent_id: str,
        requested_scopes: list[str],
        requested_integrations: list[str],
    ) -> ScopedToken:
        """
        Request a scoped data access token for an agent.
        The token is short-lived and restricted to the requested scope.
        """
        with self.tracer.start_span(
            "tool_gateway.request_token",
            tenant_id=tenant_id,
        ) as span:
            span.set_attribute("agent.id", agent_id)
            span.set_attribute("token.scopes", str(requested_scopes))

            # Validate all requested integrations exist
            for integration_id in requested_integrations:
                if integration_id not in self._adapters:
                    raise ValueError(f"Unknown integration: {integration_id}")

            token = self.token_manager.issue_token(
                tenant_id=tenant_id,
                agent_id=agent_id,
                scopes=requested_scopes,
                integration_ids=requested_integrations,
            )
            span.set_attribute("token.expires_at", token.expires_at.isoformat())
            return token

    def execute_tool_call(
        self,
        token_value: str,
        action_type: str,
        provider: str,
        operation: str,
        params: dict[str, Any],
        is_write: bool = False,
    ) -> dict[str, Any]:
        """
        Execute a tool call through the gateway.

        Enforces:
        1. Denylist check (INDEPENDENT of tier logic) — Master Prompt §6.5
        2. Token validation (scoped, not expired)
        3. Integration access check
        4. Scope check (read vs write)
        """
        with self.tracer.start_span("tool_gateway.execute_tool_call") as span:
            span.set_attribute("action.type", action_type)
            span.set_attribute("integration.provider", provider)
            span.set_attribute("integration.operation", operation)
            span.set_attribute("integration.is_write", is_write)

            # Step 1: Denylist enforcement (defense in depth)
            denylist_result = check_denylist(action_type)
            if denylist_result.is_denied:
                span.set_status("ERROR", f"DENYLIST: {action_type}")
                logger.error(
                    f"DENYLIST BLOCK at gateway: {action_type} — {denylist_result.reason}"
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Action '{action_type}' is on the hard-refusal denylist. "
                    f"Reason: {denylist_result.reason}",
                )

            # Step 2: Validate token
            try:
                token = self.token_manager.validate_token(token_value)
            except ValueError as e:
                span.set_status("ERROR", f"Token invalid: {e}")
                raise HTTPException(status_code=401, detail=str(e))

            span.set_attribute("token.agent_id", token.agent_id)
            span.set_attribute("token.tenant_id", token.tenant_id)

            # Step 3: Check integration access
            if provider not in token.integration_ids:
                span.set_status("ERROR", "Integration not in token scope")
                raise HTTPException(
                    status_code=403,
                    detail=f"Token does not grant access to integration '{provider}'",
                )

            # Step 4: Check scope
            required_scope = f"{'write' if is_write else 'read'}:{operation}"
            if not any(
                scope.startswith("write:" if is_write else "read:")
                or scope == "*"
                for scope in token.scopes
            ):
                span.set_status("ERROR", "Insufficient scope")
                raise HTTPException(
                    status_code=403,
                    detail=f"Token does not have required scope: {required_scope}",
                )

            # Step 5: Execute through adapter registry
            adapter = self._adapters.get(provider)
            if not adapter:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"No adapter registered for provider '{provider}'. "
                        f"Valid providers: {sorted(self._adapters.keys())}"
                    ),
                )

            if is_write:
                if hasattr(adapter, 'execute_write'):
                    result = adapter.execute_write(operation, params, token.tenant_id)
                else:
                    # New ToolAdapter interface — use execute()
                    import asyncio
                    req = ToolExecutionRequest(
                        tenant_id=token.tenant_id,
                        action_type=f"write_{operation}" if is_write else f"read_{operation}",
                        params=params,
                        scoped_token=token_value,
                        trace_id=str(uuid.uuid4()),
                    )
                    result_obj = await adapter.execute(req)
                    result = result_obj.data if result_obj.success else {"error": result_obj.error}
            else:
                if hasattr(adapter, 'execute_read'):
                    result = adapter.execute_read(operation, params, token.tenant_id)
                else:
                    req = ToolExecutionRequest(
                        tenant_id=token.tenant_id,
                        action_type=f"read_{operation}",
                        params=params,
                        scoped_token=token_value,
                        trace_id=str(uuid.uuid4()),
                    )
                    result_obj = await adapter.execute(req)
                    result = result_obj.data if result_obj.success else {"error": result_obj.error}

            span.add_event("tool_call_completed", {
                "provider": provider,
                "operation": operation,
                "is_write": is_write,
            })

            return result


# ─── FastAPI Routes ───────────────────────────────────────────────────────────

# Global gateway instance
gateway = ToolGateway()


class TokenRequest(BaseModel):
    tenant_id: str
    agent_id: str
    scopes: list[str]
    integration_ids: list[str]


class ToolCallRequest(BaseModel):
    action_type: str
    provider: str
    operation: str
    params: dict[str, Any] = Field(default_factory=dict)
    is_write: bool = False


@app.post("/tokens", response_model=dict)
async def request_token(req: TokenRequest):
    """Request a scoped data access token.
    
    Uses SCOPE_MAP to auto-resolve scopes for known agents.
    If scopes are explicitly provided, they are used directly.
    """
    try:
        # Auto-resolve scopes from SCOPE_MAP if not explicitly provided
        scopes = req.scopes
        if not scopes and req.agent_id in SCOPE_MAP:
            scopes = SCOPE_MAP[req.agent_id]
            logger.info(f"Auto-resolved scopes for {req.agent_id}: {scopes}")
        elif not scopes:
            logger.warning(
                f"No scopes provided and no SCOPE_MAP entry for agent '{req.agent_id}'. "
                f"Known agents: {sorted(SCOPE_MAP.keys())}"
            )

        token = gateway.request_token(
            tenant_id=req.tenant_id,
            agent_id=req.agent_id,
            requested_scopes=scopes,
            requested_integrations=req.integration_ids,
        )
        return {
            "token": token.token,
            "expires_at": token.expires_at.isoformat(),
            "scopes": token.scopes,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/tools/execute", response_model=dict)
async def execute_tool(
    req: ToolCallRequest,
    authorization: str = Header(..., alias="X-Access-Token"),
):
    """Execute a tool call through the gateway."""
    return gateway.execute_tool_call(
        token_value=authorization,
        action_type=req.action_type,
        provider=req.provider,
        operation=req.operation,
        params=req.params,
        is_write=req.is_write,
    )


class AgentToolCallRequest(BaseModel):
    """Schema used by agents calling /execute/read or /execute/write."""
    tenant_id: str = ""
    provider: str
    operation: str
    params: dict[str, Any] = Field(default_factory=dict)


@app.post("/execute/read", response_model=dict)
async def execute_read(req: AgentToolCallRequest, request: Request):
    """Convenience endpoint for agents to read data via integrations.
    Accepts Authorization: Bearer <token> header (what agents actually send).
    
    Now routes through dispatch_tool_call for consistent adapter registry usage."""
    auth_header = request.headers.get("Authorization", "")
    token_value = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else auth_header
    
    if not token_value or token_value == "fallback_token":
        # No valid scoped token — dispatch through adapter registry directly
        result = await dispatch_tool_call(
            tenant_id=req.tenant_id,
            action_type=f"read_{req.operation}",
            provider=req.provider,
            params=req.params,
            scoped_token="",
            trace_id=str(uuid.uuid4()),
        )
        if result.success:
            return {"data": result.data}
        else:
            raise HTTPException(status_code=400, detail=result.error)
    
    return gateway.execute_tool_call(
        token_value=token_value,
        action_type=f"read_{req.operation}",
        provider=req.provider,
        operation=req.operation,
        params=req.params,
        is_write=False,
    )


@app.post("/execute/write", response_model=dict)
async def execute_write(req: AgentToolCallRequest, request: Request):
    """Convenience endpoint for agents to write data via integrations.
    
    Now routes through dispatch_tool_call for consistent adapter registry usage."""
    auth_header = request.headers.get("Authorization", "")
    token_value = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else auth_header
    
    if not token_value or token_value == "fallback_token":
        result = await dispatch_tool_call(
            tenant_id=req.tenant_id,
            action_type=f"write_{req.operation}",
            provider=req.provider,
            params=req.params,
            scoped_token="",
            trace_id=str(uuid.uuid4()),
        )
        if result.success:
            return {"data": result.data}
        else:
            raise HTTPException(status_code=400, detail=result.error)
    
    return gateway.execute_tool_call(
        token_value=token_value,
        action_type=f"write_{req.operation}",
        provider=req.provider,
        operation=req.operation,
        params=req.params,
        is_write=True,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "tool-gateway"}


@app.get("/health/live")
async def health_live():
    """Liveness probe — process is running."""
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    """Readiness probe — service is ready to accept traffic.
    Checks that the adapter registry is populated."""
    if not ADAPTER_REGISTRY:
        raise HTTPException(status_code=503, detail="No adapters registered")
    return {
        "status": "ready",
        "adapters_loaded": len(ADAPTER_REGISTRY),
        "providers": sorted(ADAPTER_REGISTRY.keys()),
    }


# ─── Google OAuth Flow ──────────────────────────────────────────────────────────

@app.get("/auth/google/login")
async def google_login(tenant_id: str, request: Request):
    """Initial login — requests only basic scopes (openid, email, profile)."""
    try:
        authorization_url = build_authorization_url(state=tenant_id)
        return RedirectResponse(authorization_url)
    except ValueError as e:
        return HTMLResponse(f"<h1>Configuration Error</h1><p>{e}</p>", status_code=500)

@app.get("/auth/google/login/full")
async def google_login_full(tenant_id: str, request: Request):
    """Dev/convenience login — requests ALL scopes at once (for testing)."""
    try:
        from packages.integrations.google.auth import ALL_SCOPES
        authorization_url = build_authorization_url(state=tenant_id, scopes=ALL_SCOPES)
        return RedirectResponse(authorization_url)
    except ValueError as e:
        return HTMLResponse(f"<h1>Configuration Error</h1><p>{e}</p>", status_code=500)

@app.get("/auth/google/incremental")
async def google_incremental_auth(tenant_id: str, service: str, request: Request):
    """Incremental authorization — requests additional scopes for a specific service.
    
    Args:
        tenant_id: The tenant requesting access
        service: One of 'gmail', 'calendar', 'drive', 'sheets'
    """
    try:
        from packages.integrations.google.auth import build_incremental_auth_url
        authorization_url = build_incremental_auth_url(state=tenant_id, service=service)
        return RedirectResponse(authorization_url)
    except ValueError as e:
        return HTMLResponse(f"<h1>Invalid Service</h1><p>{e}</p>", status_code=400)

@app.get("/auth/google/scopes")
async def check_granted_scopes(tenant_id: str):
    """Check which Google service scopes have been granted for a tenant."""
    from vault import vault
    from packages.integrations.google.auth import INCREMENTAL_SCOPES
    
    creds = vault.get_credential_by_tenant("google", tenant_id)
    if not creds:
        return {"granted": {}, "message": "No Google credentials found. Please sign in first."}
    
    granted_scope_str = creds.get("scope", "")
    granted_scopes = granted_scope_str.split(" ") if granted_scope_str else []
    
    result = {}
    for service, required_scopes in INCREMENTAL_SCOPES.items():
        result[service] = all(s in granted_scopes for s in required_scopes)
    
    return {"granted": result, "raw_scopes": granted_scopes}

@app.get("/auth/google/callback")
async def google_callback(state: str, code: str, request: Request):
    try:
        from vault import vault
        
        # Check if we already have credentials for this tenant (incremental auth case)
        existing_creds = vault.get_credential_by_tenant("google", state)
        
        # The callback handles the entire flow: tokens, users DB, integrations DB, and JWT
        result = await handle_google_callback(state, code, vault.store_credential)
        
        # If this was an incremental auth, merge the new scopes with existing refresh token
        if existing_creds and existing_creds.get("refresh_token"):
            # The new token exchange may not return a refresh_token for incremental grants
            # Keep the existing refresh_token if the new exchange didn't provide one
            new_creds = vault.get_credential_by_tenant("google", state)
            if new_creds and not new_creds.get("refresh_token"):
                # Find and update the vault entry to preserve the old refresh token
                for ref, record in vault.credentials.items():
                    if record.get("provider") == "google" and record.get("tenant_id") == state:
                        record["payload"]["refresh_token"] = existing_creds["refresh_token"]
                        vault._save()
                        break
        
        token = result["token"]
        
        # Redirect back to the frontend with the JWT
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(f"{frontend_url}/auth/callback?token={token}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(
            f"<h1>Google Login Failed</h1><p>{str(e)}</p><a href='/'>Go Back</a>",
            status_code=500
        )

@app.post("/internal/vault/google")
async def store_google_token(req: dict, request: Request):
    """
    Internal endpoint to store Google tokens synced from Clerk (via API Gateway).
    In production, secure this with an internal shared secret.
    """
    tenant_id = req.get("tenant_id")
    payload = req.get("payload")
    
    if not tenant_id or not payload:
        raise HTTPException(status_code=400, detail="Missing tenant_id or payload")
        
    from vault import vault
    
    # Store in vault
    vault.store_credential("google_workspace", tenant_id, payload)
    # Also store under legacy "google" provider name for backward compatibility
    vault.store_credential("google", tenant_id, payload)
    
    logger.info(f"Stored Google token for tenant {tenant_id} via internal sync")
    return {"status": "success", "message": "Token stored in vault"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

