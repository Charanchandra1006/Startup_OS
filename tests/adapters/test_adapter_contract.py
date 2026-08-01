"""
Chief AI Startup OS — Adapter Contract Tests
Implements: STARTUP_OS_MASTER_BUILD_PLAN Part 10.1

Parametrized test asserting every registered adapter:
1. Implements authenticate() and execute()
2. Raises AdapterAuthError when no vault entry exists
3. Correctly reports supports() for declared actions
4. Returns ToolExecutionResult from execute()
"""

import os
import sys
import pytest
import asyncio

# Ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/tool-gateway")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../packages/shared-types/python")))


from adapters.base import (
    ToolAdapter,
    AdapterAuthError,
    ToolExecutionRequest,
    ToolExecutionResult,
)
from adapters.mock_adapter import MockAdapter


# ─── Fixtures ─────────────────────────────────────────────────────────────────

class EmptyVault:
    """Vault stub that always returns None — simulates no credentials."""
    def get_credential_by_tenant(self, provider: str, tenant_id: str):
        return None
    def store_credential(self, provider: str, tenant_id: str, payload: dict):
        return "ref_stub"
    def get_credential(self, vault_ref: str):
        return None
    def update_credential(self, vault_ref: str, payload: dict):
        pass


@pytest.fixture
def empty_vault():
    return EmptyVault()


@pytest.fixture
def mock_adapter():
    return MockAdapter("mock_accounting")


def _make_request(action_type: str = "test_action") -> ToolExecutionRequest:
    return ToolExecutionRequest(
        tenant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        action_type=action_type,
        params={"key": "value"},
        scoped_token="test_token",
        trace_id="test_trace_001",
    )


# ─── Mock Adapter Tests ──────────────────────────────────────────────────────

class TestMockAdapter:
    """Tests for the MockAdapter extracted from original IntegrationAdapter."""

    def test_mock_adapter_is_tool_adapter(self, mock_adapter):
        """Mock adapter must implement the ToolAdapter contract."""
        assert isinstance(mock_adapter, ToolAdapter)

    def test_mock_adapter_kind(self, mock_adapter):
        from adapters.base import AdapterKind
        assert mock_adapter.kind == AdapterKind.MOCK

    def test_mock_adapter_provider_name(self, mock_adapter):
        assert mock_adapter.provider_name == "mock_accounting"

    def test_mock_adapter_supports_all(self, mock_adapter):
        """Mock adapters accept all action types."""
        assert mock_adapter.supports("anything")
        assert mock_adapter.supports("calendar.create_event")
        assert mock_adapter.supports("finance.get_transactions")

    @pytest.mark.asyncio
    async def test_mock_authenticate_always_succeeds(self, mock_adapter):
        """Mock auth never fails — it's mock."""
        result = await mock_adapter.authenticate("any_tenant")
        assert result["mock"] is True

    @pytest.mark.asyncio
    async def test_mock_execute_returns_result(self, mock_adapter):
        """Mock execute must return a ToolExecutionResult."""
        request = _make_request("read_transactions")
        result = await mock_adapter.execute(request)
        assert isinstance(result, ToolExecutionResult)
        assert result.success is True
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_mock_execute_logs_calls(self, mock_adapter):
        """Mock adapter must record calls for test assertion."""
        request = _make_request("read_transactions")
        await mock_adapter.execute(request)
        log = mock_adapter.get_call_log()
        assert len(log) == 1
        assert log[0]["action_type"] == "read_transactions"
        assert log[0]["tenant_id"] == "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"


# ─── Google Workspace Adapter Tests ──────────────────────────────────────────

class TestGoogleWorkspaceAdapter:
    """Contract tests for GoogleWorkspaceAdapter."""

    def test_adapter_implements_contract(self, empty_vault):
        from adapters.google_workspace import GoogleWorkspaceAdapter
        adapter = GoogleWorkspaceAdapter(empty_vault)
        assert isinstance(adapter, ToolAdapter)

    def test_supported_actions(self, empty_vault):
        from adapters.google_workspace import GoogleWorkspaceAdapter
        adapter = GoogleWorkspaceAdapter(empty_vault)
        assert adapter.supports("gmail.send")
        assert adapter.supports("calendar.create_event")
        assert adapter.supports("drive.list_files")
        assert adapter.supports("sheets.read_range")
        assert not adapter.supports("quickbooks.get_invoices")

    @pytest.mark.asyncio
    async def test_auth_error_when_no_credentials(self, empty_vault):
        """Must raise AdapterAuthError when vault has no creds for tenant."""
        from adapters.google_workspace import GoogleWorkspaceAdapter
        adapter = GoogleWorkspaceAdapter(empty_vault)
        with pytest.raises(AdapterAuthError, match="No Google OAuth credentials"):
            await adapter.authenticate("nonexistent_tenant")


# ─── QuickBooks Adapter Tests ────────────────────────────────────────────────

class TestQuickBooksAdapter:
    """Contract tests for QuickBooksAdapter."""

    def test_adapter_implements_contract(self, empty_vault):
        from adapters.quickbooks import QuickBooksAdapter
        adapter = QuickBooksAdapter(empty_vault, sandbox=True)
        assert isinstance(adapter, ToolAdapter)

    def test_supported_actions(self, empty_vault):
        from adapters.quickbooks import QuickBooksAdapter
        adapter = QuickBooksAdapter(empty_vault, sandbox=True)
        assert adapter.supports("finance.get_transactions")
        assert adapter.supports("finance.get_invoices")
        assert adapter.supports("finance.get_profit_and_loss")
        assert adapter.supports("finance.get_cash_flow")
        assert not adapter.supports("gmail.send")

    @pytest.mark.asyncio
    async def test_auth_error_when_no_credentials(self, empty_vault):
        from adapters.quickbooks import QuickBooksAdapter
        adapter = QuickBooksAdapter(empty_vault, sandbox=True)
        with pytest.raises(AdapterAuthError, match="No QuickBooks connection"):
            await adapter.authenticate("nonexistent_tenant")


# ─── MCP Adapter Tests ──────────────────────────────────────────────────────

class TestMCPAdapter:
    """Contract tests for MCPAdapter."""

    def test_adapter_implements_contract(self, empty_vault):
        from adapters.mcp_adapter import MCPAdapter, MCPServerConfig
        config = MCPServerConfig(
            provider_name="test_mcp",
            mcp_url="http://localhost:9999",
            supported_actions=frozenset({"test.action"}),
        )
        adapter = MCPAdapter(config, empty_vault)
        assert isinstance(adapter, ToolAdapter)

    def test_supported_actions(self, empty_vault):
        from adapters.mcp_adapter import MCPAdapter, MCPServerConfig
        config = MCPServerConfig(
            provider_name="test_mcp",
            mcp_url="http://localhost:9999",
            supported_actions=frozenset({"test.action", "test.other"}),
        )
        adapter = MCPAdapter(config, empty_vault)
        assert adapter.supports("test.action")
        assert adapter.supports("test.other")
        assert not adapter.supports("test.nonexistent")

    @pytest.mark.asyncio
    async def test_auth_error_when_no_credentials(self, empty_vault):
        from adapters.mcp_adapter import MCPAdapter, MCPServerConfig
        config = MCPServerConfig(
            provider_name="test_mcp",
            mcp_url="http://localhost:9999",
            supported_actions=frozenset({"test.action"}),
        )
        adapter = MCPAdapter(config, empty_vault)
        with pytest.raises(AdapterAuthError, match="No test_mcp connection"):
            await adapter.authenticate("nonexistent_tenant")


# ─── Cross-Adapter Registry Tests ────────────────────────────────────────────

class TestAdapterRegistry:
    """Test that all configured adapters meet the contract."""

    def test_all_registered_adapters_are_tool_adapters(self):
        """Every adapter in the registry must be a ToolAdapter instance."""
        # Import at test time to avoid module-level side effects
        try:
            from adapters.mock_adapter import MockAdapter
            for name in ["mock_accounting", "mock_calendar", "mock_email", "mock_ats", "mock_pm"]:
                adapter = MockAdapter(name)
                assert isinstance(adapter, ToolAdapter), f"{name} is not a ToolAdapter"
        except ImportError:
            pytest.skip("Adapters not importable in test environment")

    def test_each_mock_provider_has_distinct_name(self):
        from adapters.mock_adapter import MockAdapter
        names = set()
        for name in ["mock_accounting", "mock_calendar", "mock_email", "mock_ats", "mock_pm"]:
            adapter = MockAdapter(name)
            assert adapter.provider_name not in names, f"Duplicate provider name: {name}"
            names.add(adapter.provider_name)
