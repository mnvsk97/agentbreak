"""Abstract transport interface for MCP communications."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agentbreak.mcp_protocol import MCPRequest

# Default timeout for upstream requests (seconds).
DEFAULT_TRANSPORT_TIMEOUT = 30.0


class MCPTransport(ABC):
    """Abstract base class for MCP transport implementations.

    Subclasses must implement `send_request`, `start`, and `stop`.
    The lifecycle is:
        1. Optionally call `start()` to initialise resources.
        2. Call `send_request()` one or more times.
        3. Call `stop()` to release resources.

    `send_request` may call `start()` lazily if the transport has not yet been
    started, so explicit `start()` calls are optional in simple scenarios.
    """

    @abstractmethod
    async def send_request(self, request: MCPRequest) -> dict[str, Any]:
        """Send an MCP request and return the raw JSON-RPC response dict.

        Raises:
            TimeoutError: If the upstream does not respond in time.
            RuntimeError: If the connection is broken or unusable.
            OSError: If a low-level I/O error occurs.
        """

    @abstractmethod
    async def start(self) -> None:
        """Initialise any long-lived resources (connections, subprocesses, etc.)."""

    @abstractmethod
    async def stop(self) -> None:
        """Release all resources held by this transport."""
