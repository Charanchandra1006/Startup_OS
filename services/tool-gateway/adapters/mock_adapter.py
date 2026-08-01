"""
Chief AI Startup OS — Mock Adapter
Extracted from tool_gateway.py's IntegrationAdapter for dev/demo use.

This adapter conforms to the ToolAdapter interface so dev mode uses
the exact same dispatch path as production — only the adapter behind
the registry entry differs.

Supported mock providers: mock_accounting, mock_calendar, mock_email, mock_ats, mock_pm
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .base import (
    ToolAdapter,
    AdapterKind,
    ToolExecutionRequest,
    ToolExecutionResult,
)

logger = logging.getLogger("chief.tool_gateway.adapters.mock")


# ─── Mock response data (extracted from original IntegrationAdapter) ──────────

MOCK_RESPONSES: dict[str, dict[str, Any]] = {
    "mock_accounting": {
        "_default": {
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
    },
    "mock_calendar": {
        "_default": {
            "executives": [
                {"name": "Charan Chandra (Founder/CEO)", "email": "charan@visionai.com", "timezone": "EST"},
                {"name": "Sarah Jenkins (CFO)", "email": "cfo@visionai.com", "timezone": "EST"},
                {"name": "David Wu (CTO)", "email": "cto@visionai.com", "timezone": "PST"},
                {"name": "Elena Rostova (VP Growth)", "email": "growth@visionai.com", "timezone": "EST"},
            ],
            "existing_events": [
                {
                    "id": "evt_1", "title": "Weekly Growth Pipeline Review",
                    "attendees": ["charan@visionai.com", "growth@visionai.com", "cfo@visionai.com"],
                    "current_slot": "Thursdays 2:00 PM EST", "status": "frequent_conflicts_noted",
                },
                {
                    "id": "evt_2", "title": "Engineering Sprint Planning",
                    "attendees": ["cto@visionai.com", "charan@visionai.com"],
                    "slot": "Mondays 11:00 AM EST",
                },
            ],
            "proposed_slots": [
                {"slot": "Tuesdays 10:00 AM EST", "conflicts": "None - All executives free"},
                {"slot": "Wednesdays 1:00 PM EST", "conflicts": "None - All executives free"},
            ],
        }
    },
    "mock_email": {
        "_default": {
            "recent_emails": [
                {
                    "from": "growth@visionai.com",
                    "subject": "Growth Review conflict",
                    "body": "Thursday 2pm conflicts with our client demos. Can we move the Weekly Growth Pipeline Review to Tuesdays at 10 AM EST?",
                },
                {
                    "from": "cfo@visionai.com",
                    "subject": "Re: Growth Review",
                    "body": "Tuesday 10 AM EST works great for my calendar as well.",
                },
            ]
        }
    },
    "mock_ats": {
        "_default": {
            "candidates": [
                {"name": "Jane Smith", "role": "Senior Engineer", "status": "interview_scheduled"},
                {"name": "Bob Johnson", "role": "Product Manager", "status": "offer_pending"},
            ],
        }
    },
    "mock_pm": {
        "_default": {
            "projects": [
                {"name": "Q4 Launch", "status": "on_track", "completion": 72},
                {"name": "API v2", "status": "at_risk", "completion": 45},
            ],
        }
    },
}


class MockAdapter(ToolAdapter):
    """Mock adapter for development and demo environments.

    Conforms to the ToolAdapter interface so the dispatch path is identical
    to production — only the data source differs. Supports read and write
    operations with realistic mock responses.
    """

    kind = AdapterKind.MOCK

    def __init__(self, mock_provider: str):
        """
        Args:
            mock_provider: One of 'mock_accounting', 'mock_calendar',
                'mock_email', 'mock_ats', 'mock_pm'.
        """
        self.provider_name = mock_provider
        self._mock_data = MOCK_RESPONSES.get(mock_provider, {})
        self._call_log: list[dict[str, Any]] = []

        # Mock adapters accept all action types
        self.supported_actions = frozenset({"*"})

    async def authenticate(self, tenant_id: str) -> dict[str, Any]:
        """Mock authentication always succeeds."""
        return {"tenant_id": tenant_id, "provider": self.provider_name, "mock": True}

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Return mock data. Logs the call for test inspection."""
        call_record = {
            "provider": self.provider_name,
            "action_type": request.action_type,
            "params": request.params,
            "tenant_id": request.tenant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._call_log.append(call_record)
        logger.info(
            f"Mock adapter [{self.provider_name}] executing: "
            f"{request.action_type}"
        )

        # Return the default mock response for this provider
        data = self._mock_data.get("_default", {
            "data": [],
            "message": f"Mock response for {self.provider_name}/{request.action_type}",
        })

        return ToolExecutionResult(
            success=True,
            data=data,
            provider_latency_ms=15.0,  # simulated latency
        )

    def supports(self, action_type: str) -> bool:
        """Mock adapters accept all action types."""
        return True

    def get_call_log(self) -> list[dict[str, Any]]:
        """Return the log of all mock calls for test assertions."""
        return list(self._call_log)
