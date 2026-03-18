"""HTTP transport for MCP."""

from __future__ import annotations

import json
from typing import Any

import httpx

from agentbreak.protocols.mcp import MCPRequest
from agentbreak.transports.base import DEFAULT_TRANSPORT_TIMEOUT, MCPTransport


class HTTPTransport(MCPTransport):
    """Transport that forwards MCP requests to an upstream HTTP server.

    Maintains a persistent httpx.AsyncClient for connection reuse with a
    configurable connection pool.  The client is created on `start()` (or
    lazily on first `send_request()`) and closed on `stop()`.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = DEFAULT_TRANSPORT_TIMEOUT,
        extra_headers: dict[str, str] | None = None,
        max_connections: int = 10,
        max_keepalive_connections: int = 5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.extra_headers = extra_headers or {}
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self._client: httpx.AsyncClient | None = None
        self._started = False

    async def start(self) -> None:
        """Create the HTTP client (optional; happens lazily on first request)."""
        if not self._started:
            self._started = True
            limits = httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_keepalive_connections,
            )
            self._client = httpx.AsyncClient(timeout=self.timeout, limits=limits)

    async def send_request(self, request: MCPRequest) -> dict[str, Any]:
        if not self._started:
            await self.start()
        assert self._client is not None
        headers = {"Content-Type": "application/json", **self.extra_headers}
        body = request.to_json_bytes()
        try:
            response = await self._client.post(
                f"{self.base_url}/mcp",
                content=body,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            raise RuntimeError(f"HTTP upstream error: {exc}") from exc
        try:
            return response.json()
        except (json.JSONDecodeError, ValueError, AttributeError) as exc:
            raise RuntimeError(f"HTTP upstream returned non-JSON response: {exc}") from exc

    async def stop(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._started = False
