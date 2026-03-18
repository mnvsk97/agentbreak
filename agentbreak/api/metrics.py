"""Metrics and scorecard endpoints for AgentBreak services."""

from __future__ import annotations

from fastapi import FastAPI

from agentbreak.core.statistics import StatisticsTracker


def setup_metrics_routes(
    app: FastAPI,
    service_name: str,
    stats: StatisticsTracker,
) -> None:
    """Setup metrics and scorecard endpoints."""

    @app.get("/_agentbreak/scorecard")
    async def get_scorecard() -> dict:
        return stats.generate_scorecard(service_name)

    @app.get("/_agentbreak/requests")
    async def get_recent_requests() -> dict:
        service_stats = stats.get_service_stats(service_name)
        return {"recent_requests": service_stats.recent_requests}
