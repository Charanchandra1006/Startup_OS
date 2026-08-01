"""
Chief AI Startup OS — MCP Adapter Wrapper (Generic)
Implements: STARTUP_OS_MASTER_BUILD_PLAN Part 2.5

One generic class, config-driven, so adding a 5th/6th MCP server is a
config entry, not new code. Phase 2 — GitHub, Slack, Notion, Linear.

All MCP adapters still pass through the same tier-classifier and denylist
enforcement as REST adapters (see tool_gateway.py dispatch_tool_call),
so the safety model doesn't fork.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from .base import (
    ToolAdapter,
    AdapterKind,
    AdapterAuthError,
    AdapterProviderUnavailable,
    AdapterRateLimitError,
    ToolExecutionRequest,
    ToolExecutionResult,
)

logger = logging.getLogger("chief.tool_gateway.adapters.mcp")


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server endpoint."""
    provider_name: str
    mcp_url: str
    supported_actions: frozenset[str]
    auth_header_name: str = "Authorization"


class MCPAdapter(ToolAdapter):
    """Generic wrapper for any MCP server reachable over HTTP/SSE transport.

    One instance per configured server (github, slack, notion, linear).
    Config-driven: adding a new MCP server requires only a new
    MCPServerConfig entry in MCP_SERVER_CONFIGS, not a new Python file.
    """

    kind = AdapterKind.MCP

    def __init__(self, config: MCPServerConfig, vault):
        self.config = config
        self.provider_name = config.provider_name
        self.supported_actions = config.supported_actions
        self.vault = vault
        self._client = httpx.AsyncClient(timeout=20.0)

    async def authenticate(self, tenant_id: str) -> dict[str, Any]:
        """Retrieve MCP server credentials for a tenant from the vault."""
        stored = self.vault.get_credential_by_tenant(
            self.provider_name, tenant_id
        )
        if stored is None:
            raise AdapterAuthError(
                f"No {self.provider_name} connection for tenant {tenant_id}. "
                f"Founder must connect {self.provider_name} first."
            )
        return stored

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Call the MCP server's /tools/call endpoint."""
        if not self.supports(request.action_type):
            return ToolExecutionResult(
                success=False, data=None,
                error=(
                    f"{self.provider_name} MCP adapter does not support "
                    f"{request.action_type}"
                ),
            )

        start = time.monotonic()
        try:
            creds = await self.authenticate(request.tenant_id)
            token = creds.get("access_token", "")

            resp = await self._client.post(
                f"{self.config.mcp_url}/tools/call",
                json={
                    "tool": request.action_type,
                    "arguments": request.params,
                },
                headers={
                    self.config.auth_header_name: f"Bearer {token}",
                },
            )
            resp.raise_for_status()
            elapsed_ms = (time.monotonic() - start) * 1000
            return ToolExecutionResult(
                success=True, data=resp.json(), provider_latency_ms=elapsed_ms
            )

        except AdapterAuthError:
            raise
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                raise AdapterAuthError(
                    f"{self.provider_name} MCP rejected credentials"
                ) from exc
            if exc.response.status_code == 429:
                raise AdapterRateLimitError(
                    f"{self.provider_name} MCP rate limit hit"
                ) from exc
            raise AdapterProviderUnavailable(
                f"{self.provider_name} MCP error: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise AdapterProviderUnavailable(
                f"{self.provider_name} MCP timed out"
            ) from exc


# ─── Phase 2 MCP Server Registry ─────────────────────────────────────────────
# Add entries here — no new Python files needed per tool.
# Replace placeholder URLs with actual MCP server endpoints when deploying.

MCP_SERVER_CONFIGS = [
    MCPServerConfig(
        provider_name="github",
        mcp_url="https://mcp.github.com",  # replace with actual endpoint
        supported_actions=frozenset({
            "github.list_issues",
            "github.create_issue",
            "github.get_pr_status",
            "github.list_repos",
        }),
    ),
    MCPServerConfig(
        provider_name="slack",
        mcp_url="https://mcp.slack.com",  # replace with actual endpoint
        supported_actions=frozenset({
            "slack.post_message",
            "slack.read_channel",
            "slack.list_channels",
        }),
    ),
    MCPServerConfig(
        provider_name="notion",
        mcp_url="https://mcp.notion.com",  # replace with actual endpoint
        supported_actions=frozenset({
            "notion.search",
            "notion.read_page",
            "notion.create_page",
        }),
    ),
    MCPServerConfig(
        provider_name="linear",
        mcp_url="https://mcp.linear.app",  # replace with actual endpoint
        supported_actions=frozenset({
            "linear.list_issues",
            "linear.create_issue",
            "linear.update_issue",
        }),
    ),
]
