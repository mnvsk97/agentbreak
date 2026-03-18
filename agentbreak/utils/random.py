"""Random utility functions for fault and latency injection."""

from __future__ import annotations

import random


def clamp_probability(value: float) -> float:
    """Clamp a probability value to [0.0, 1.0]."""
    return max(0.0, min(1.0, value))


def should_inject(probability: float) -> bool:
    """Return True with the given probability (clamped to [0, 1])."""
    return random.random() < clamp_probability(probability)
