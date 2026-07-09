"""
Tests for Tool/Integration Gateway
Implements: Testing Strategy §2 (denylist at gateway), §3 (token scoping)

Tests that:
1. Denylist enforcement blocks all 6 hard-denied actions at the gateway layer
2. Token scoping limits integration access
3. Expired tokens are rejected
4. Revoked tokens are rejected
5. Out-of-scope integration calls are blocked
"""

import pytest
import time
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'packages', 'shared-types', 'python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from chief_types.observability import reset_tracer
from tool_gateway import ToolGateway, TokenManager, IntegrationAdapter


@pytest.fixture(autouse=True)
def reset():
    reset_tracer()


@pytest.fixture
def gateway():
    gw = ToolGateway()
    gw._register_mock_adapters()
    return gw


TENANT_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"


# ============================================================================
# Denylist Enforcement at Gateway (Master Prompt §6.5 — defense in depth)
# ============================================================================

class TestGatewayDenylist:
    """Denylist is enforced HERE independently of tier logic."""

    @pytest.mark.parametrize("action_type", [
        "contract_sign",
        "wire_transfer",
        "offer_letter_send",
        "termination",
        "compensation_change",
        "public_statement",
    ])
    def test_denied_action_blocked_at_gateway(self, gateway: ToolGateway, action_type: str):
        """Each of the 6 hard-denied actions is blocked at the gateway."""
        token = gateway.request_token(
            tenant_id=TENANT_ID,
            agent_id="AGT-FIN",
            requested_scopes=["read:transactions", "write:transfers"],
            requested_integrations=["mock_accounting"],
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            gateway.execute_tool_call(
                token_value=token.token,
                action_type=action_type,
                provider="mock_accounting",
                operation="test",
                params={},
            )
        assert exc_info.value.status_code == 403
        assert "denylist" in exc_info.value.detail.lower()

    def test_allowed_action_passes_gateway(self, gateway: ToolGateway):
        """Non-denylist actions pass through the gateway normally."""
        token = gateway.request_token(
            tenant_id=TENANT_ID,
            agent_id="AGT-FIN",
            requested_scopes=["read:transactions"],
            requested_integrations=["mock_accounting"],
        )

        result = gateway.execute_tool_call(
            token_value=token.token,
            action_type="generate_report",
            provider="mock_accounting",
            operation="transactions",
            params={},
        )
        assert "transactions" in result


# ============================================================================
# Token Scoping Tests
# ============================================================================

class TestTokenScoping:
    """Test that tokens are properly scoped and enforced."""

    def test_token_grants_access_to_specified_integration(self, gateway: ToolGateway):
        token = gateway.request_token(
            tenant_id=TENANT_ID,
            agent_id="AGT-FIN",
            requested_scopes=["read:transactions"],
            requested_integrations=["mock_accounting"],
        )

        result = gateway.execute_tool_call(
            token_value=token.token,
            action_type="generate_report",
            provider="mock_accounting",
            operation="transactions",
            params={},
        )
        assert result is not None

    def test_token_blocks_unscoped_integration(self, gateway: ToolGateway):
        """Token for mock_accounting cannot access mock_calendar."""
        token = gateway.request_token(
            tenant_id=TENANT_ID,
            agent_id="AGT-FIN",
            requested_scopes=["read:transactions"],
            requested_integrations=["mock_accounting"],
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            gateway.execute_tool_call(
                token_value=token.token,
                action_type="schedule_meeting",
                provider="mock_calendar",
                operation="create_event",
                params={},
            )
        assert exc_info.value.status_code == 403

    def test_expired_token_rejected(self, gateway: ToolGateway):
        """Expired tokens are rejected immediately."""
        token = gateway.token_manager.issue_token(
            tenant_id=TENANT_ID,
            agent_id="AGT-FIN",
            scopes=["read:transactions"],
            integration_ids=["mock_accounting"],
            ttl_seconds=0,  # Expires immediately
        )

        import time
        time.sleep(0.1)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            gateway.execute_tool_call(
                token_value=token.token,
                action_type="generate_report",
                provider="mock_accounting",
                operation="test",
                params={},
            )
        assert exc_info.value.status_code == 401

    def test_revoked_token_rejected(self, gateway: ToolGateway):
        """Revoked tokens are rejected even before expiry."""
        token = gateway.request_token(
            tenant_id=TENANT_ID,
            agent_id="AGT-FIN",
            requested_scopes=["read:transactions"],
            requested_integrations=["mock_accounting"],
        )

        gateway.token_manager.revoke_token(token.token)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            gateway.execute_tool_call(
                token_value=token.token,
                action_type="generate_report",
                provider="mock_accounting",
                operation="test",
                params={},
            )
        assert exc_info.value.status_code == 401

    def test_invalid_token_rejected(self, gateway: ToolGateway):
        """Completely fabricated tokens are rejected."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            gateway.execute_tool_call(
                token_value="fake-token-value-12345",
                action_type="generate_report",
                provider="mock_accounting",
                operation="test",
                params={},
            )
        assert exc_info.value.status_code == 401


# ============================================================================
# Token Manager Unit Tests
# ============================================================================

class TestTokenManager:
    """Unit tests for the TokenManager itself."""

    def test_issue_and_validate(self):
        tm = TokenManager()
        token = tm.issue_token(
            tenant_id=TENANT_ID,
            agent_id="AGT-FIN",
            scopes=["read:transactions"],
            integration_ids=["mock_accounting"],
        )
        validated = tm.validate_token(token.token)
        assert validated.tenant_id == TENANT_ID
        assert validated.agent_id == "AGT-FIN"

    def test_cleanup_expired(self):
        tm = TokenManager()
        tm.issue_token(
            tenant_id=TENANT_ID,
            agent_id="AGT-FIN",
            scopes=["read:transactions"],
            integration_ids=["mock_accounting"],
            ttl_seconds=0,
        )
        time.sleep(0.1)
        cleaned = tm.cleanup_expired()
        assert cleaned == 1

    def test_each_token_is_unique(self):
        tm = TokenManager()
        tokens = set()
        for _ in range(100):
            t = tm.issue_token(
                tenant_id=TENANT_ID,
                agent_id="AGT-FIN",
                scopes=["read:transactions"],
                integration_ids=["mock_accounting"],
            )
            tokens.add(t.token)
        assert len(tokens) == 100
