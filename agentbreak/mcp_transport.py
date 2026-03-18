"""Compatibility shim for mcp_transport.

The transport implementations have moved to agentbreak.transports.
This module re-exports everything for backward compatibility.
"""

from agentbreak.transports import (
    DEFAULT_TRANSPORT_TIMEOUT,
    HTTPTransport,
    MCPTransport,
    SSETransport,
    StdioTransport,
    create_transport,
)

__all__ = [
    "MCPTransport",
    "StdioTransport",
    "SSETransport",
    "HTTPTransport",
    "create_transport",
    "DEFAULT_TRANSPORT_TIMEOUT",
]
