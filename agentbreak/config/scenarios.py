"""Built-in fault scenarios for LLM and MCP services."""

from __future__ import annotations

from typing import Any


SCENARIOS: dict[str, dict[str, Any]] = {
    # LLM Scenarios
    "mixed-transient": {
        "fault": {
            "available_codes": [429, 500, 503],
            "per_error_rates": {429: 0.3, 500: 0.4, 503: 0.3},
        },
        "latency": {"probability": 0.0},
    },
    "rate-limited": {
        "fault": {
            "available_codes": [429],
            "overall_rate": 0.5,
        }
    },
    "brownout": {
        "fault": {
            "available_codes": [429, 500, 503],
            "overall_rate": 0.3,
        },
        "latency": {"probability": 0.2, "min_seconds": 5, "max_seconds": 15},
    },
    # MCP Scenarios
    "mcp-tool-failures": {
        "fault": {
            "available_codes": [429, 500, 503],
            "overall_rate": 0.3,
        },
        "latency": {"probability": 0.0},
    },
    "mcp-resource-unavailable": {
        "fault": {
            "available_codes": [404, 503],
            "overall_rate": 0.5,
        }
    },
    "mcp-slow-tools": {
        "fault": {"overall_rate": 0.0},
        "latency": {"probability": 0.9, "min_seconds": 5, "max_seconds": 15},
    },
    "mcp-initialization-failure": {
        "fault": {
            "available_codes": [500, 503],
            "overall_rate": 0.5,
        }
    },
    "mcp-mixed-transient": {
        "fault": {
            "available_codes": [429, 500, 503],
            "overall_rate": 0.2,
        },
        "latency": {"probability": 0.1, "min_seconds": 5, "max_seconds": 15},
    },
}


def apply_scenario(config: dict[str, Any], scenario_name: str) -> dict[str, Any]:
    """Apply a scenario to a configuration dict via deep merge."""
    scenario = SCENARIOS.get(scenario_name, {})
    result = config.copy()
    for key, value in scenario.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = {**result[key], **value}
        else:
            result[key] = value
    return result
