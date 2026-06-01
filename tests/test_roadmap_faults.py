"""Tests for the deprecated_library and model_deprecated faults."""
from __future__ import annotations

from fastapi.testclient import TestClient

from agentbreak import main
from agentbreak.config import MCPRegistry, MCPTool
from agentbreak.scenarios import ScenarioFile


CHAT_BODY = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}


def _make_llm_runtime(scenarios_raw):
    scenarios = ScenarioFile.model_validate({"scenarios": scenarios_raw}).scenarios
    return main.LLMRuntime(mode="mock", upstream_url="", auth_headers={}, scenarios=scenarios)


def _llm_scenario(name, fault):
    return {"name": name, "summary": name, "target": "llm_chat", "fault": fault, "schedule": {"mode": "always"}}


def _setup_mcp(scenarios_raw):
    scenarios = ScenarioFile.model_validate({"scenarios": scenarios_raw}).scenarios
    main.service_state.mcp_runtime = main.MCPRuntime(
        upstream_url="", auth_headers={},
        registry=MCPRegistry(tools=[MCPTool(name="search", description="Search docs", inputSchema={"type": "object"})]),
        scenarios=scenarios,
    )
    return TestClient(main.app)


# ── deprecated_library ───────────────────────────────────────────────


def test_deprecated_library_is_registered():
    from agentbreak.faults import REGISTRY
    assert "deprecated_library" in REGISTRY
    assert REGISTRY["deprecated_library"].category == "reliability"


def test_deprecated_library_injects_into_llm_response():
    main.service_state.llm_runtime = _make_llm_runtime([
        _llm_scenario("deplib", {"kind": "deprecated_library"}),
    ])
    client = TestClient(main.app)
    r = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    # Payload recommends known deprecated/vulnerable packages
    assert "left-pad" in content or "request@2.88.0" in content


def test_deprecated_library_injects_into_mcp_tool_result():
    client = _setup_mcp([{
        "name": "deplib-mcp", "summary": "x", "target": "mcp_tool",
        "fault": {"kind": "deprecated_library"}, "schedule": {"mode": "always"},
    }])
    r = client.post("/mcp", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "search", "arguments": {}},
    })
    assert r.status_code == 200
    text = r.json()["result"]["content"][0]["text"]
    assert "left-pad" in text or "request@2.88.0" in text


# ── model_deprecated ─────────────────────────────────────────────────


def test_model_deprecated_is_registered():
    from agentbreak.faults import REGISTRY
    assert "model_deprecated" in REGISTRY
    assert "llm_chat" in REGISTRY["model_deprecated"].targets


def test_model_deprecated_returns_410():
    main.service_state.llm_runtime = _make_llm_runtime([
        _llm_scenario("sunset", {"kind": "model_deprecated"}),
    ])
    client = TestClient(main.app)
    r = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert r.status_code == 410


def test_model_deprecated_validates_in_scenario_file():
    from agentbreak.scenarios import validate_scenarios
    sf = ScenarioFile.model_validate({"scenarios": [
        _llm_scenario("sunset", {"kind": "model_deprecated"}),
    ]})
    validate_scenarios(sf)  # should not raise


# ── return_error honors manifest status (regression guard) ───────────


def test_return_error_falls_back_to_manifest_status():
    """not_found's manifest declares status 404; without an explicit status_code
    the proxy used to return 500. It should now honor the manifest."""
    main.service_state.llm_runtime = _make_llm_runtime([
        _llm_scenario("nf", {"kind": "not_found"}),
    ])
    client = TestClient(main.app)
    r = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert r.status_code == 404


def test_explicit_status_code_still_wins():
    main.service_state.llm_runtime = _make_llm_runtime([
        _llm_scenario("nf", {"kind": "not_found", "status_code": 418}),
    ])
    client = TestClient(main.app)
    r = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert r.status_code == 418


# ── inject_text faults are now actually applied ──────────────────────


def test_indirect_injection_now_injects_on_mcp():
    """Regression guard: inject_text catalog faults used to be silent no-ops on
    the request path. The payload should now appear in the tool result."""
    client = _setup_mcp([{
        "name": "indirect", "summary": "x", "target": "mcp_tool",
        "fault": {"kind": "indirect_injection"}, "schedule": {"mode": "always"},
    }])
    r = client.post("/mcp", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "search", "arguments": {}},
    })
    text = r.json()["result"]["content"][0]["text"]
    # original mock result is preserved, payload is appended
    assert "mock result for search" in text
    assert len(text) > len("mock result for search")


def test_inject_text_explicit_payload_override():
    client = _setup_mcp([{
        "name": "indirect", "summary": "x", "target": "mcp_tool",
        "fault": {"kind": "indirect_injection", "payload": "SENTINEL_INJECT"},
        "schedule": {"mode": "always"},
    }])
    r = client.post("/mcp", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "search", "arguments": {}},
    })
    assert "SENTINEL_INJECT" in r.json()["result"]["content"][0]["text"]
