"""HTTP client pooling utilities."""

from __future__ import annotations

import httpx


def make_async_client(
    timeout: float = 120.0,
    max_connections: int = 10,
    max_keepalive_connections: int = 5,
) -> httpx.AsyncClient:
    """Create an httpx.AsyncClient with a connection pool."""
    limits = httpx.Limits(
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive_connections,
    )
    return httpx.AsyncClient(timeout=timeout, limits=limits)
