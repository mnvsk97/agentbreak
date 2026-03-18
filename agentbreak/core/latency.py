"""Latency injection for AgentBreak proxy services."""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING, Optional

from agentbreak.config.models import LatencyConfig

if TYPE_CHECKING:
    from agentbreak.core.proxy import ProxyContext


class LatencyInjector:
    """Handles latency injection for proxy services."""

    def __init__(self, config: LatencyConfig) -> None:
        self.config = config

    async def maybe_delay(self, context: "ProxyContext") -> Optional[float]:
        """Inject delay if configured probability triggers.

        Returns the injected delay in seconds if latency was injected,
        otherwise None.
        """
        if not self.config.enabled or self.config.probability == 0:
            return None

        if random.random() >= self.config.probability:
            return None

        delay = random.uniform(self.config.min_seconds, self.config.max_seconds)
        await asyncio.sleep(delay)
        context.metadata["latency_injected"] = delay
        return delay
