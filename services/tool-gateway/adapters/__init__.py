"""
Chief AI Startup OS — Tool Adapter Package
All adapters (REST, MCP, Mock) live here. The ToolAdapter ABC in base.py
defines the contract; tool_gateway.py's ADAPTER_REGISTRY loads them at startup.
"""

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

__all__ = [
    "ToolAdapter",
    "AdapterKind",
    "AdapterError",
    "AdapterAuthError",
    "AdapterRateLimitError",
    "AdapterProviderUnavailable",
    "ToolExecutionRequest",
    "ToolExecutionResult",
]
