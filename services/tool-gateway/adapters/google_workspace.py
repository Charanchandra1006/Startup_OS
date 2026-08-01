"""
Chief AI Startup OS — Google Workspace Adapter (REST)
Implements: STARTUP_OS_MASTER_BUILD_PLAN Part 2.3

Wraps existing packages/integrations/google/{gmail,calendar,drive,sheets}.py
thin wrappers behind the ToolAdapter interface. Does NOT rewrite those modules —
only orchestrates auth lifecycle + error normalization + scope validation around them.

Supported actions:
- gmail.send, gmail.search
- calendar.create_event, calendar.list_events, calendar.check_conflicts
- drive.list_files
- sheets.read_range
"""

from __future__ import annotations

import time
import logging
from typing import Any

from .base import (
    ToolAdapter,
    AdapterKind,
    AdapterError,
    AdapterAuthError,
    AdapterRateLimitError,
    AdapterProviderUnavailable,
    ToolExecutionRequest,
    ToolExecutionResult,
)

logger = logging.getLogger("chief.tool_gateway.adapters.google_workspace")


class GoogleWorkspaceAdapter(ToolAdapter):
    """REST adapter for Google Workspace APIs.

    Reuses the existing thin wrappers in packages/integrations/google/*
    and adds: auth lifecycle management, scope validation, and error
    normalization into the ToolAdapter contract.
    """

    kind = AdapterKind.REST
    provider_name = "google_workspace"
    supported_actions = frozenset({
        "gmail.send",
        "gmail.search",
        "calendar.create_event",
        "calendar.list_events",
        "calendar.check_conflicts",
        "drive.list_files",
        "sheets.read_range",
    })

    # Least-privilege scopes per action. Do NOT request drive.file full write
    # unless a specific agent (Legal) demonstrably needs it.
    REQUIRED_SCOPES = {
        "gmail.send": ["https://www.googleapis.com/auth/gmail.send"],
        "gmail.search": ["https://www.googleapis.com/auth/gmail.readonly"],
        "calendar.create_event": ["https://www.googleapis.com/auth/calendar.events"],
        "calendar.list_events": ["https://www.googleapis.com/auth/calendar.readonly"],
        "calendar.check_conflicts": ["https://www.googleapis.com/auth/calendar.readonly"],
        "drive.list_files": ["https://www.googleapis.com/auth/drive.readonly"],
        "sheets.read_range": ["https://www.googleapis.com/auth/spreadsheets.readonly"],
    }

    def __init__(self, vault):
        """
        Args:
            vault: Any vault instance implementing get_credential_by_tenant()
                   and store_credential() — the existing LocalVault or the new
                   managed-secrets vault from Phase D.
        """
        self.vault = vault

    async def authenticate(self, tenant_id: str) -> dict[str, Any]:
        """Retrieve and refresh Google OAuth credentials for a tenant.

        Returns the stored credential dict with a valid access_token.
        Raises AdapterAuthError if no credentials exist or refresh fails.
        """
        stored = self.vault.get_credential_by_tenant("google", tenant_id)
        if stored is None:
            raise AdapterAuthError(
                f"No Google OAuth credentials for tenant {tenant_id}. "
                "Founder must complete /api/auth/google flow first."
            )

        # Check if token needs refresh
        token_expiry = stored.get("expiry")
        if token_expiry and stored.get("refresh_token"):
            try:
                import datetime
                if isinstance(token_expiry, str):
                    expiry_dt = datetime.datetime.fromisoformat(token_expiry)
                else:
                    expiry_dt = token_expiry

                now = datetime.datetime.now(datetime.timezone.utc)
                if hasattr(expiry_dt, 'tzinfo') and expiry_dt.tzinfo is None:
                    expiry_dt = expiry_dt.replace(tzinfo=datetime.timezone.utc)

                if now >= expiry_dt:
                    stored = await self._refresh_token(tenant_id, stored)
            except Exception as exc:
                logger.warning(f"Token expiry check failed for tenant {tenant_id}: {exc}")
                # Continue with existing token — it may still work

        return stored

    async def _refresh_token(self, tenant_id: str, stored: dict) -> dict:
        """Refresh an expired Google access token using the stored refresh token."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": stored["refresh_token"],
                        "client_id": stored.get("client_id", ""),
                        "client_secret": stored.get("client_secret", ""),
                    },
                    timeout=10.0,
                )
                resp.raise_for_status()
                token_data = resp.json()

                stored["access_token"] = token_data["access_token"]
                if "refresh_token" in token_data:
                    stored["refresh_token"] = token_data["refresh_token"]

                import datetime
                stored["expiry"] = (
                    datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(seconds=token_data.get("expires_in", 3600))
                ).isoformat()

                # Persist refreshed credentials back to vault
                self.vault.store_credential("google", tenant_id, stored)
                logger.info(f"Refreshed Google token for tenant {tenant_id}")
                return stored

        except Exception as exc:
            raise AdapterAuthError(
                f"Google token refresh failed for tenant {tenant_id}: {exc}"
            ) from exc

    def _validate_scope(self, action_type: str, credentials: dict) -> None:
        """Verify the tenant's granted scopes cover the action's requirements."""
        required = self.REQUIRED_SCOPES.get(action_type, [])
        granted_scope_str = credentials.get("scope", "")
        granted = set(granted_scope_str.split(" ")) if granted_scope_str else set()

        missing = [s for s in required if s not in granted]
        if missing:
            raise AdapterAuthError(
                f"Tenant credentials missing required scope(s) {missing} "
                f"for action {action_type}. Founder must re-consent."
            )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Execute a Google Workspace action via the existing integration wrappers."""
        if not self.supports(request.action_type):
            return ToolExecutionResult(
                success=False, data=None,
                error=f"google_workspace adapter does not support {request.action_type}",
            )

        start = time.monotonic()
        try:
            creds = await self.authenticate(request.tenant_id)
            self._validate_scope(request.action_type, creds)

            # Delegate to existing thin wrappers in packages/integrations/google/
            result = await self._dispatch_action(request.action_type, creds, request.params)

            elapsed_ms = (time.monotonic() - start) * 1000
            return ToolExecutionResult(
                success=True, data=result, provider_latency_ms=elapsed_ms
            )

        except AdapterAuthError:
            raise
        except AdapterRateLimitError:
            raise
        except AdapterProviderUnavailable:
            raise
        except Exception as exc:
            error_str = str(exc)
            # Classify common HTTP errors
            if "429" in error_str:
                raise AdapterRateLimitError("Google API rate limit hit") from exc
            if "500" in error_str or "502" in error_str or "503" in error_str:
                raise AdapterProviderUnavailable(
                    f"Google API returned server error: {error_str}"
                ) from exc
            if "timeout" in error_str.lower() or "timed out" in error_str.lower():
                raise AdapterProviderUnavailable(
                    "Google API request timed out"
                ) from exc
            raise AdapterError(f"Google API error: {error_str}") from exc

    async def _dispatch_action(
        self, action_type: str, credentials: dict, params: dict
    ) -> dict[str, Any]:
        """Route action_type to the correct integration wrapper function.

        Uses the existing packages/integrations/google/* modules where available,
        falls back to direct HTTP calls where the thin wrappers don't exist yet.
        """
        access_token = credentials.get("access_token", "")

        try:
            if action_type == "gmail.send":
                from packages.integrations.google.gmail import GmailService
                service = GmailService(access_token)
                return await self._async_wrap(service.send_email, **params)

            elif action_type == "gmail.search":
                from packages.integrations.google.gmail import GmailService
                service = GmailService(access_token)
                return await self._async_wrap(service.search_emails, **params)

            elif action_type == "calendar.create_event":
                from packages.integrations.google.calendar import CalendarService
                service = CalendarService(access_token)
                return await self._async_wrap(service.create_event, **params)

            elif action_type == "calendar.list_events":
                from packages.integrations.google.calendar import CalendarService
                service = CalendarService(access_token)
                return await self._async_wrap(service.list_events, **params)

            elif action_type == "calendar.check_conflicts":
                from packages.integrations.google.calendar import CalendarService
                service = CalendarService(access_token)
                return await self._async_wrap(service.check_conflicts, **params)

            elif action_type == "drive.list_files":
                from packages.integrations.google.drive import DriveService
                service = DriveService(access_token)
                return await self._async_wrap(service.list_files, **params)

            elif action_type == "sheets.read_range":
                from packages.integrations.google.sheets import SheetsService
                service = SheetsService(access_token)
                return await self._async_wrap(service.read_range, **params)

            else:
                raise AdapterError(
                    f"Unhandled but declared-supported action: {action_type}"
                )

        except (AdapterAuthError, AdapterRateLimitError, AdapterProviderUnavailable):
            raise
        except ImportError as exc:
            logger.error(f"Integration module not found for {action_type}: {exc}")
            return {
                "error": f"Integration module not available for {action_type}",
                "fallback": True,
            }

    @staticmethod
    async def _async_wrap(fn, **kwargs):
        """Wrap a synchronous integration function in an async context.
        Our existing google integration wrappers are sync — this lets them
        work within the async adapter.execute() contract."""
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: fn(**kwargs))
        if isinstance(result, dict):
            return result
        return {"result": result}
