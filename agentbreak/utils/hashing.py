"""Fingerprinting and hashing utilities."""

from __future__ import annotations

import hashlib


def fingerprint_bytes(data: bytes) -> str:
    """Return a SHA-256 hex fingerprint of the given bytes."""
    return hashlib.sha256(data).hexdigest()
