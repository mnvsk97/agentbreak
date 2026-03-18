"""Health check endpoints for AgentBreak services."""

from __future__ import annotations

from fastapi import FastAPI


def setup_health_routes(app: FastAPI, service_name: str) -> None:
    """Setup health check endpoints."""

    @app.get("/healthz")
    async def health_check() -> dict:
        return {"status": "ok", "service": service_name}
