from __future__ import annotations

import pytest

from agentbreak import main
from agentbreak.config import ApplicationConfig, MCPRegistry
from agentbreak.scenarios import ScenarioFile
from tests.helpers import DummyAsyncClient, DummyResponse


@pytest.fixture(autouse=True)
def reset_global_state() -> None:
    main.service_state = main.ServiceState(
        application=ApplicationConfig.model_validate(
            {
                "llm": {"enabled": True, "mode": "proxy", "upstream_url": "https://upstream.example"},
                "mcp": {"enabled": False},
                "serve": {"host": "127.0.0.1", "port": 5005},
            }
        ),
        scenarios=ScenarioFile(),
        registry=MCPRegistry(),
        llm_runtime=main.LLMRuntime(
            mode="proxy",
            upstream_url="https://upstream.example",
            auth_headers={},
            scenarios=[],
        ),
        mcp_runtime=None,
    )
    DummyAsyncClient.calls = []
    DummyAsyncClient.responses = []
    DummyAsyncClient.error = None
    DummyAsyncClient.response = DummyResponse()
