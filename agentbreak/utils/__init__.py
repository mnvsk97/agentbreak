"""Utility functions for AgentBreak."""

from agentbreak.utils.hashing import fingerprint_bytes
from agentbreak.utils.headers import filter_headers
from agentbreak.utils.random import clamp_probability, should_inject

__all__ = [
    "clamp_probability",
    "should_inject",
    "filter_headers",
    "fingerprint_bytes",
]
