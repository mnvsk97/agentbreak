"""API route setup modules for AgentBreak services."""

from .health import setup_health_routes
from .metrics import setup_metrics_routes

__all__ = ["setup_health_routes", "setup_metrics_routes"]
