"""HTTP header filtering utilities."""

from __future__ import annotations

import httpx


_SKIP_HEADERS = frozenset({"host", "content-length"})


def filter_headers(headers: httpx.Headers) -> dict[str, str]:
    """Filter out hop-by-hop and sensitive headers for proxying."""
    return {key: value for key, value in headers.items() if key.lower() not in _SKIP_HEADERS}
