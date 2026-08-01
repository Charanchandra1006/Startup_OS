"""
Chief AI Startup OS — QuickBooks Adapter (REST)
Implements: STARTUP_OS_MASTER_BUILD_PLAN Part 2.4

New integration (no existing wrapper in packages/integrations/).
Provides Finance Agent access to real QuickBooks data via the Intuit API.

Supported actions:
- finance.get_transactions
- finance.get_invoices
- finance.get_profit_and_loss
- finance.get_cash_flow
"""

from __future__ import annotations

import time
import logging
from typing import Any

import httpx

from .base import (
    ToolAdapter,
    AdapterKind,
    AdapterAuthError,
    AdapterRateLimitError,
    AdapterProviderUnavailable,
    ToolExecutionRequest,
    ToolExecutionResult,
)

logger = logging.getLogger("chief.tool_gateway.adapters.quickbooks")

QUICKBOOKS_API_BASE = "https://quickbooks.api.intuit.com/v3/company"
QUICKBOOKS_SANDBOX_API_BASE = "https://sandbox-quickbooks.api.intuit.com/v3/company"


class QuickBooksAdapter(ToolAdapter):
    """REST adapter for QuickBooks Online API.

    Provides the Finance Agent with real transaction, invoice, and
    reporting data from a founder's QuickBooks account.
    """

    kind = AdapterKind.REST
    provider_name = "quickbooks"
    supported_actions = frozenset({
        "finance.get_transactions",
        "finance.get_invoices",
        "finance.get_profit_and_loss",
        "finance.get_cash_flow",
    })

    def __init__(self, vault, sandbox: bool = False):
        """
        Args:
            vault: Vault instance for credential storage/retrieval.
            sandbox: If True, use QuickBooks sandbox API (for dev/testing).
        """
        self.vault = vault
        self._base_url = QUICKBOOKS_SANDBOX_API_BASE if sandbox else QUICKBOOKS_API_BASE
        self._client = httpx.AsyncClient(timeout=15.0)

    async def authenticate(self, tenant_id: str) -> dict[str, Any]:
        """Retrieve and refresh QuickBooks OAuth credentials for a tenant."""
        stored = self.vault.get_credential_by_tenant("quickbooks", tenant_id)
        if stored is None:
            raise AdapterAuthError(
                f"No QuickBooks connection for tenant {tenant_id}. "
                "Founder must complete QuickBooks OAuth flow first."
            )

        # Check if token is expired
        if stored.get("expires_at", 0) <= time.time():
            stored = await self._refresh_token(tenant_id, stored)

        return stored

    async def _refresh_token(self, tenant_id: str, stored: dict) -> dict:
        """Refresh an expired QuickBooks access token."""
        try:
            resp = await self._client.post(
                "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": stored["refresh_token"],
                },
                auth=(stored.get("client_id", ""), stored.get("client_secret", "")),
            )
            resp.raise_for_status()
            token_data = resp.json()

            stored["access_token"] = token_data["access_token"]
            stored["refresh_token"] = token_data.get(
                "refresh_token", stored["refresh_token"]
            )
            stored["expires_at"] = time.time() + token_data.get("expires_in", 3600)

            # Persist refreshed credentials
            self.vault.store_credential("quickbooks", tenant_id, stored)
            logger.info(f"Refreshed QuickBooks token for tenant {tenant_id}")
            return stored

        except httpx.HTTPStatusError as exc:
            raise AdapterAuthError(
                f"QuickBooks token refresh failed: {exc.response.status_code}"
            ) from exc
        except Exception as exc:
            raise AdapterAuthError(
                f"QuickBooks token refresh error: {exc}"
            ) from exc

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Execute a QuickBooks API query."""
        if not self.supports(request.action_type):
            return ToolExecutionResult(
                success=False, data=None,
                error=f"quickbooks adapter does not support {request.action_type}",
            )

        start = time.monotonic()
        try:
            creds = await self.authenticate(request.tenant_id)
            realm_id = creds.get("realm_id", "")
            headers = {
                "Authorization": f"Bearer {creds['access_token']}",
                "Accept": "application/json",
            }

            resp = await self._dispatch_action(
                request.action_type, realm_id, headers, request.params
            )

            resp.raise_for_status()
            elapsed_ms = (time.monotonic() - start) * 1000
            return ToolExecutionResult(
                success=True, data=resp.json(), provider_latency_ms=elapsed_ms
            )

        except AdapterAuthError:
            raise
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise AdapterAuthError(
                    "QuickBooks token rejected — re-auth required"
                ) from exc
            if exc.response.status_code == 429:
                raise AdapterRateLimitError(
                    "QuickBooks rate limit hit"
                ) from exc
            if exc.response.status_code >= 500:
                raise AdapterProviderUnavailable(
                    f"QuickBooks returned {exc.response.status_code}"
                ) from exc
            elapsed_ms = (time.monotonic() - start) * 1000
            return ToolExecutionResult(
                success=False, data=None,
                error=f"QuickBooks API error: {exc.response.status_code} {exc.response.text}",
                provider_latency_ms=elapsed_ms,
            )
        except httpx.TimeoutException as exc:
            raise AdapterProviderUnavailable(
                "QuickBooks request timed out"
            ) from exc

    async def _dispatch_action(
        self,
        action_type: str,
        realm_id: str,
        headers: dict,
        params: dict,
    ) -> httpx.Response:
        """Route action_type to the correct QuickBooks API endpoint."""
        if action_type == "finance.get_transactions":
            query = params.get("query", "SELECT * FROM Purchase MAXRESULTS 100")
            return await self._client.get(
                f"{self._base_url}/{realm_id}/query",
                params={"query": query},
                headers=headers,
            )

        elif action_type == "finance.get_invoices":
            query = params.get("query", "SELECT * FROM Invoice MAXRESULTS 100")
            return await self._client.get(
                f"{self._base_url}/{realm_id}/query",
                params={"query": query},
                headers=headers,
            )

        elif action_type == "finance.get_profit_and_loss":
            return await self._client.get(
                f"{self._base_url}/{realm_id}/reports/ProfitAndLoss",
                params=params,
                headers=headers,
            )

        elif action_type == "finance.get_cash_flow":
            return await self._client.get(
                f"{self._base_url}/{realm_id}/reports/CashFlow",
                params=params,
                headers=headers,
            )

        else:
            raise ValueError(f"Unhandled QuickBooks action: {action_type}")
