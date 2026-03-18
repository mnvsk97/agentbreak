"""Transport layer for MCP communications."""

from agentbreak.transports.base import DEFAULT_TRANSPORT_TIMEOUT, MCPTransport
from agentbreak.transports.http import HTTPTransport
from agentbreak.transports.sse import SSETransport
from agentbreak.transports.stdio import StdioTransport


def create_transport(
    transport_type: str,
    *,
    base_url: str = "",
    command: tuple[str, ...] = (),
    timeout: float = DEFAULT_TRANSPORT_TIMEOUT,
    extra_headers: dict[str, str] | None = None,
    max_connections: int = 10,
    max_keepalive_connections: int = 5,
) -> MCPTransport:
    """Factory function to create a transport by type name.

    Args:
        transport_type: One of "stdio", "sse", "http".
        base_url: Required for "sse" and "http" transports.
        command: Required for "stdio" transport.
        timeout: Request/connection timeout in seconds.
        extra_headers: Optional extra headers for HTTP/SSE transports.
        max_connections: Maximum number of connections in the pool (http/sse).
        max_keepalive_connections: Maximum number of idle keep-alive connections (http/sse).

    Returns:
        An MCPTransport instance ready for use.

    Raises:
        ValueError: If transport_type is unknown or required args are missing.
    """
    if transport_type == "stdio":
        if not command:
            raise ValueError("command is required for stdio transport")
        return StdioTransport(command=command, timeout=timeout)
    if transport_type == "sse":
        if not base_url:
            raise ValueError("base_url is required for sse transport")
        return SSETransport(
            base_url=base_url,
            timeout=timeout,
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
        )
    if transport_type == "http":
        if not base_url:
            raise ValueError("base_url is required for http transport")
        return HTTPTransport(
            base_url=base_url,
            timeout=timeout,
            extra_headers=extra_headers,
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
        )
    raise ValueError(
        f"Unknown transport type '{transport_type}'. Must be one of: stdio, sse, http"
    )


__all__ = [
    "MCPTransport",
    "StdioTransport",
    "SSETransport",
    "HTTPTransport",
    "create_transport",
    "DEFAULT_TRANSPORT_TIMEOUT",
]
