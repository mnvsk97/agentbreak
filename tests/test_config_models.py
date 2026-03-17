"""Unit tests for agentbreak.config.models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentbreak.config.models import (
    AgentBreakConfig,
    FaultConfig,
    LatencyConfig,
    MCPServiceConfig,
    OpenAIServiceConfig,
    ServiceType,
    TransportType,
)


# ---------------------------------------------------------------------------
# FaultConfig
# ---------------------------------------------------------------------------

class TestFaultConfig:
    def test_defaults(self):
        fc = FaultConfig()
        assert fc.enabled is True
        assert fc.overall_rate == 0.1
        assert fc.available_codes == (429, 500, 503)

    def test_invalid_rate_above_1(self):
        with pytest.raises(ValidationError):
            FaultConfig(overall_rate=1.5)

    def test_invalid_rate_below_0(self):
        with pytest.raises(ValidationError):
            FaultConfig(overall_rate=-0.1)

    def test_disabled_returns_none(self):
        fc = FaultConfig(enabled=False)
        # With fault disabled, get_fault_code must always return None
        for _ in range(50):
            assert fc.get_fault_code() is None

    def test_always_injects_when_rate_1(self):
        fc = FaultConfig(
            enabled=True,
            overall_rate=1.0,
            per_error_rates={},
            available_codes=(500,),
        )
        # With overall_rate=1.0 and no per_error_rates, should always return 500
        results = {fc.get_fault_code() for _ in range(20)}
        assert results == {500}

    def test_never_injects_when_rate_0(self):
        fc = FaultConfig(
            enabled=True,
            overall_rate=0.0,
            per_error_rates={},
            available_codes=(500,),
        )
        for _ in range(50):
            assert fc.get_fault_code() is None

    def test_returns_available_code(self):
        fc = FaultConfig(
            enabled=True,
            overall_rate=1.0,
            per_error_rates={},
            available_codes=(429, 503),
        )
        for _ in range(30):
            code = fc.get_fault_code()
            assert code in (429, 503)


# ---------------------------------------------------------------------------
# LatencyConfig
# ---------------------------------------------------------------------------

class TestLatencyConfig:
    def test_defaults(self):
        lc = LatencyConfig()
        assert lc.enabled is True
        assert lc.probability == 0.0
        assert lc.min_seconds == 5.0
        assert lc.max_seconds == 15.0

    def test_invalid_probability(self):
        with pytest.raises(ValidationError):
            LatencyConfig(probability=2.0)

    def test_negative_min(self):
        with pytest.raises(ValidationError):
            LatencyConfig(min_seconds=-1.0)


# ---------------------------------------------------------------------------
# OpenAIServiceConfig
# ---------------------------------------------------------------------------

class TestOpenAIServiceConfig:
    def test_basic_construction(self):
        svc = OpenAIServiceConfig(name="llm", port=5000)
        assert svc.type == ServiceType.OPENAI
        assert svc.mode == "proxy"
        assert svc.upstream_url == "https://api.openai.com"
        assert svc.upstream_timeout == 120.0

    def test_custom_upstream(self):
        svc = OpenAIServiceConfig(name="llm", port=5000, upstream_url="http://localhost:8080")
        assert svc.upstream_url == "http://localhost:8080"

    def test_fault_and_latency_defaults(self):
        svc = OpenAIServiceConfig(name="llm", port=5000)
        assert isinstance(svc.fault, FaultConfig)
        assert isinstance(svc.latency, LatencyConfig)


# ---------------------------------------------------------------------------
# MCPServiceConfig
# ---------------------------------------------------------------------------

class TestMCPServiceConfig:
    def test_basic_construction(self):
        svc = MCPServiceConfig(name="mcp", port=6000)
        assert svc.type == ServiceType.MCP
        assert svc.upstream_transport == TransportType.HTTP
        assert svc.cache_ttl == 60.0

    def test_stdio_transport(self):
        svc = MCPServiceConfig(
            name="mcp",
            port=6000,
            upstream_transport=TransportType.STDIO,
            upstream_command=("python", "-m", "myserver"),
        )
        assert svc.upstream_transport == TransportType.STDIO
        assert svc.upstream_command == ("python", "-m", "myserver")

    def test_mock_data_defaults(self):
        svc = MCPServiceConfig(name="mcp", port=6000)
        assert svc.mock_tools == []
        assert svc.mock_resources == []
        assert svc.mock_prompts == []


# ---------------------------------------------------------------------------
# AgentBreakConfig
# ---------------------------------------------------------------------------

class TestAgentBreakConfig:
    def test_empty_services(self):
        cfg = AgentBreakConfig()
        assert cfg.services == []
        assert cfg.version == "1.0"

    def test_single_service(self):
        svc = OpenAIServiceConfig(name="llm", port=5000)
        cfg = AgentBreakConfig(services=[svc])
        assert len(cfg.services) == 1

    def test_duplicate_port_raises(self):
        svc1 = OpenAIServiceConfig(name="llm1", port=5000)
        svc2 = OpenAIServiceConfig(name="llm2", port=5000)
        with pytest.raises(ValidationError, match="ports must be unique"):
            AgentBreakConfig(services=[svc1, svc2])

    def test_unique_ports_ok(self):
        svc1 = OpenAIServiceConfig(name="llm", port=5000)
        svc2 = MCPServiceConfig(name="mcp", port=6000)
        cfg = AgentBreakConfig(services=[svc1, svc2])
        assert len(cfg.services) == 2

    def test_get_service_found(self):
        svc = OpenAIServiceConfig(name="llm", port=5000)
        cfg = AgentBreakConfig(services=[svc])
        found = cfg.get_service("llm")
        assert found.name == "llm"

    def test_get_service_not_found(self):
        cfg = AgentBreakConfig()
        with pytest.raises(ValueError, match="not found"):
            cfg.get_service("missing")
