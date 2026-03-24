from fastapi.testclient import TestClient
from agentbreak import main
from agentbreak.config import MCPRegistry, MCPTool, MCPResource, MCPPrompt
from agentbreak.scenarios import ScenarioFile

def _setup_mcp(scenarios_data=None):
    """Helper to set up MCP runtime with tools and optional scenarios."""
    scenarios = []
    if scenarios_data:
        scenarios = ScenarioFile.model_validate({"scenarios": scenarios_data}).scenarios
    main.service_state.mcp_runtime = main.MCPRuntime(
        upstream_url="", auth_headers={},
        registry=MCPRegistry(
            tools=[MCPTool(name="search", description="Search", inputSchema={"type": "object"})],
            resources=[MCPResource(uri="file:///doc.md", name="doc", mimeType="text/markdown")],
            prompts=[MCPPrompt(name="summarize", description="Summarize")],
        ),
        scenarios=scenarios,
    )
    return TestClient(main.app)

# Test all fault kinds on MCP tools
def test_mcp_http_error_on_tool_call():
    client = _setup_mcp([{"name": "err", "summary": "err", "target": "mcp_tool", "match": {"tool_name": "search"}, "fault": {"kind": "http_error", "status_code": 503}, "schedule": {"mode": "always"}}])
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search", "arguments": {}}})
    assert r.status_code == 503

def test_mcp_timeout_on_tool_call():
    client = _setup_mcp([{"name": "to", "summary": "to", "target": "mcp_tool", "match": {"tool_name": "search"}, "fault": {"kind": "timeout", "min_ms": 1, "max_ms": 1}, "schedule": {"mode": "always"}}])
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search", "arguments": {}}})
    assert r.status_code == 504

def test_mcp_empty_response_on_tool_call():
    client = _setup_mcp([{"name": "empty", "summary": "empty", "target": "mcp_tool", "match": {"tool_name": "search"}, "fault": {"kind": "empty_response"}, "schedule": {"mode": "always"}}])
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search", "arguments": {}}})
    assert r.status_code == 200
    assert r.content == b""

def test_mcp_invalid_json_on_tool_call():
    client = _setup_mcp([{"name": "bad", "summary": "bad", "target": "mcp_tool", "match": {"tool_name": "search"}, "fault": {"kind": "invalid_json"}, "schedule": {"mode": "always"}}])
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search", "arguments": {}}})
    assert r.content == b"{not valid"

def test_mcp_wrong_content_on_tool_call():
    client = _setup_mcp([{"name": "wrong", "summary": "wrong", "target": "mcp_tool", "match": {"tool_name": "search"}, "fault": {"kind": "wrong_content", "body": "HACKED"}, "schedule": {"mode": "always"}}])
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search", "arguments": {}}})
    assert r.status_code == 200
    assert "HACKED" in r.json()["result"]["content"][0]["text"]

def test_mcp_large_response_on_tool_call():
    client = _setup_mcp([{"name": "large", "summary": "large", "target": "mcp_tool", "match": {"tool_name": "search"}, "fault": {"kind": "large_response", "size_bytes": 5000}, "schedule": {"mode": "always"}}])
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search", "arguments": {}}})
    assert r.status_code == 200
    assert len(r.json()["result"]["content"][0]["text"]) >= 5000

# Schema violation on resources and prompts
def test_mcp_schema_violation_on_resource():
    client = _setup_mcp([{"name": "sv", "summary": "sv", "target": "mcp_tool", "fault": {"kind": "schema_violation"}, "schedule": {"mode": "always"}}])
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "resources/read", "params": {"uri": "file:///doc.md"}})
    assert r.json()["result"]["contents"] == "INVALID"

def test_mcp_schema_violation_on_prompt():
    client = _setup_mcp([{"name": "sv", "summary": "sv", "target": "mcp_tool", "fault": {"kind": "schema_violation"}, "schedule": {"mode": "always"}}])
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "prompts/get", "params": {"name": "summarize"}})
    assert r.json()["result"]["messages"] == "INVALID"

# MCP latency (not timeout — request still succeeds)
def test_mcp_latency_still_returns_result():
    client = _setup_mcp([{"name": "slow", "summary": "slow", "target": "mcp_tool", "fault": {"kind": "latency", "min_ms": 1, "max_ms": 2}, "schedule": {"mode": "always"}}])
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search", "arguments": {}}})
    assert r.status_code == 200
    assert "result" in r.json()

# MCP disabled returns 404
def test_mcp_disabled_returns_404():
    main.service_state.mcp_runtime = None
    client = TestClient(main.app)
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert r.status_code == 404

# MCP unknown method
def test_mcp_unknown_method():
    client = _setup_mcp()
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "foo/bar", "params": {}})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == -32601

# Empty body
def test_mcp_empty_body():
    client = _setup_mcp()
    r = client.post("/mcp", content=b"", headers={"content-type": "application/json"})
    assert r.status_code == 200  # empty body returns empty response

# Scorecard
def test_mcp_scorecard_pass():
    client = _setup_mcp()
    client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search", "arguments": {}}})
    sc = client.get("/_agentbreak/mcp-scorecard").json()
    assert sc["run_outcome"] == "PASS"
    assert sc["resilience_score"] == 100

def test_mcp_scorecard_fail_on_injected_errors():
    client = _setup_mcp([{"name": "err", "summary": "err", "target": "mcp_tool", "fault": {"kind": "http_error", "status_code": 500}, "schedule": {"mode": "always"}}])
    client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search", "arguments": {}}})
    client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "search", "arguments": {"q": "b"}}})
    sc = client.get("/_agentbreak/mcp-scorecard").json()
    assert sc["run_outcome"] == "FAIL"
    assert sc["resilience_score"] < 100
