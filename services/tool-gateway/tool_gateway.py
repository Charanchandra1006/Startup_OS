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

logger = logging.getLogger("chief.tool_gateway")

app = FastAPI(
    title="Chief Tool/Integration Gateway",
    description="MCP-compatible gateway for all external integrations. SAD §2, SGD §6.5.",
    version="0.1.0",
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
        ttl = ttl_seconds or self.DEFAULT_TTL_SECONDS
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
                ],
                "summary": {"monthly_burn": 50000, "runway_months": 12},
            }
        return {"data": [], "message": f"Mock response for {self.provider}/{operation}"}

    def get_call_log(self) -> list[dict[str, Any]]:
        return list(self._call_log)


# ─── Gateway Service ─────────────────────────────────────────────────────────

class ToolGateway:
    """
    Central gateway for all external integrations.
    Enforces denylist, token scoping, and audit logging.
    """

    def __init__(self):
        self.token_manager = TokenManager()
        self._adapters: dict[str, IntegrationAdapter] = {}
        self.tracer = get_tracer("tool-gateway")
        self._register_mock_adapters()
        
        # Register real adapters
        try:
            from packages.integrations.google import GoogleIntegrationAdapter
            from vault import vault
            self.register_adapter("google", GoogleIntegrationAdapter(vault))
        except ImportError as e:
            logger.warning(f"Could not load Google adapter: {e}")

    def _register_mock_adapters(self):
        """Register mock adapters for Phase 0."""
        self._adapters["mock_accounting"] = IntegrationAdapter("mock_accounting")
        self._adapters["mock_calendar"] = IntegrationAdapter("mock_calendar")
        self._adapters["mock_email"] = IntegrationAdapter("mock_email")
        self._adapters["mock_ats"] = IntegrationAdapter("mock_ats")
        self._adapters["mock_pm"] = IntegrationAdapter("mock_pm")

    def register_adapter(self, provider: str, adapter: IntegrationAdapter) -> None:
        """Register a new integration adapter."""
        self._adapters[provider] = adapter

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

            # Step 5: Execute through adapter
            adapter = self._adapters.get(provider)
            if not adapter:
                raise HTTPException(
                    status_code=404,
                    detail=f"No adapter registered for provider '{provider}'",
                )

            if is_write:
                result = adapter.execute_write(operation, params, token.tenant_id)
            else:
                result = adapter.execute_read(operation, params, token.tenant_id)

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
    """Request a scoped data access token."""
    try:
        token = gateway.request_token(
            tenant_id=req.tenant_id,
            agent_id=req.agent_id,
            requested_scopes=req.scopes,
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


@app.get("/health")
async def health():
    return {"status": "ok", "service": "tool-gateway"}


# ─── Google OAuth Flow ──────────────────────────────────────────────────────────

@app.get("/auth/google/login")
async def google_login(tenant_id: str, request: Request):
    try:
        authorization_url = build_authorization_url(state=tenant_id)
        return RedirectResponse(authorization_url)
    except ValueError as e:
        return HTMLResponse(f"<h1>Configuration Error</h1><p>{e}</p>", status_code=500)

@app.get("/auth/google/callback")
async def google_callback(state: str, code: str, request: Request):
    try:
        from vault import vault
        # The callback handles the entire flow: tokens, users DB, integrations DB, and JWT
        result = await handle_google_callback(state, code, vault.store_credential)
        
        token = result["token"]
        user = result["user"]
        
        # Redirect back to the frontend with the JWT
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3001")
        return RedirectResponse(f"{frontend_url}/auth/callback?token={token}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(
            f"<h1>Google Login Failed</h1><p>{str(e)}</p><a href='/'>Go Back</a>",
            status_code=500
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
