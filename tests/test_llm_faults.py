from __future__ import annotations

from fastapi.testclient import TestClient

from agentbreak import main
from agentbreak.scenarios import ScenarioFile


CHAT_BODY = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}


def _make_runtime(scenarios_raw=None, mode="mock", upstream_url="", auth_headers=None):
    scenarios = []
    if scenarios_raw is not None:
        scenarios = ScenarioFile.model_validate({"scenarios": scenarios_raw}).scenarios
    return main.LLMRuntime(
        mode=mode,
        upstream_url=upstream_url,
        auth_headers=auth_headers or {},
        scenarios=scenarios,
    )


def _scenario(name, fault, schedule=None):
    return {
        "name": name,
        "summary": name,
        "target": "llm_chat",
        "fault": fault,
        "schedule": schedule or {"mode": "always"},
    }


# ── Mutation fault kinds ─────────────────────────────────────────────


def test_llm_empty_response_scenario():
    """empty_response returns 200 with empty body"""
    main.service_state.llm_runtime = _make_runtime([
        _scenario("empty", {"kind": "empty_response"}),
    ])
    client = TestClient(main.app)
    r = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert r.status_code == 200
    assert r.content == b""


def test_llm_wrong_content_scenario():
    """wrong_content replaces message content with custom body"""
    main.service_state.llm_runtime = _make_runtime([
        _scenario("wrong", {"kind": "wrong_content", "body": "REPLACED"}),
    ])
    client = TestClient(main.app)
    r = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert r.status_code == 200
    data = r.json()
    assert data["choices"][0]["message"]["content"] == "REPLACED"


def test_llm_wrong_content_default_body():
    """wrong_content without custom body uses default message"""
    main.service_state.llm_runtime = _make_runtime([
        _scenario("wrong-default", {"kind": "wrong_content"}),
    ])
    client = TestClient(main.app)
    r = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert r.status_code == 200
    data = r.json()
    assert "AgentBreak injected wrong content" in data["choices"][0]["message"]["content"]


def test_llm_large_response_scenario():
    """large_response returns oversized body"""
    main.service_state.llm_runtime = _make_runtime([
        _scenario("large", {"kind": "large_response", "size_bytes": 10000}),
    ])
    client = TestClient(main.app)
    r = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert r.status_code == 200
    assert len(r.content) >= 10000


def test_llm_schema_violation_scenario():
    """schema_violation corrupts tool_calls field"""
    main.service_state.llm_runtime = _make_runtime([
        _scenario("schema", {"kind": "schema_violation"}),
    ])
    client = TestClient(main.app)
    r = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert r.status_code == 200
    data = r.json()
    assert data["choices"][0]["message"]["tool_calls"] == "INVALID"


def test_llm_latency_scenario_still_returns_data():
    """latency adds delay but response is normal"""
    main.service_state.llm_runtime = _make_runtime([
        _scenario("latency", {"kind": "latency", "min_ms": 1, "max_ms": 2}),
    ])
    client = TestClient(main.app)
    r = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert r.status_code == 200
    data = r.json()
    assert data["model"] == "agentbreak-mock"
    assert data["choices"][0]["message"]["content"] == "AgentBreak mock response."


# ── Mock mode ────────────────────────────────────────────────────────


def test_llm_mock_mode_returns_synthetic_completion():
    main.service_state.llm_runtime = _make_runtime()
    client = TestClient(main.app)
    r = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert r.status_code == 200
    data = r.json()
    assert data["model"] == "agentbreak-mock"
    assert data["choices"][0]["message"]["content"] == "AgentBreak mock response."


# ── Proxy upstream failures ──────────────────────────────────────────


def test_llm_proxy_upstream_unreachable(monkeypatch):
    """When upstream is down, return 502"""
    import httpx
    from tests.helpers import DummyAsyncClient

    DummyAsyncClient.error = httpx.ConnectError("refused")
    monkeypatch.setattr(main.httpx, "AsyncClient", DummyAsyncClient)
    main.service_state.llm_runtime = _make_runtime(
        mode="proxy", upstream_url="http://bad-host:9999",
    )
    client = TestClient(main.app)
    r = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert r.status_code == 502
    assert "upstream" in r.json()["error"]["message"].lower()


def test_llm_proxy_upstream_returns_error(monkeypatch):
    """When upstream returns 4xx/5xx, forward it"""
    from tests.helpers import DummyAsyncClient, DummyResponse

    DummyAsyncClient.response = DummyResponse(
        status_code=429, content=b'{"error":"rate limited"}',
    )
    monkeypatch.setattr(main.httpx, "AsyncClient", DummyAsyncClient)
    main.service_state.llm_runtime = _make_runtime(
        mode="proxy", upstream_url="http://upstream.example",
    )
    client = TestClient(main.app)
    r = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert r.status_code == 429


# ── Scorecard ────────────────────────────────────────────────────────


def test_llm_scorecard_pass_when_no_failures():
    main.service_state.llm_runtime = _make_runtime()
    client = TestClient(main.app)
    client.post("/v1/chat/completions", json=CHAT_BODY)
    sc = client.get("/_agentbreak/scorecard").json()
    assert sc["run_outcome"] == "PASS"
    assert sc["resilience_score"] == 100
    assert sc["requests_seen"] == 1


def test_llm_scorecard_degraded_on_faults():
    main.service_state.llm_runtime = _make_runtime([
        _scenario("err", {"kind": "http_error", "status_code": 500}),
    ])
    client = TestClient(main.app)
    client.post("/v1/chat/completions", json={"model": "m", "messages": [{"role": "user", "content": "1"}]})
    client.post("/v1/chat/completions", json={"model": "m", "messages": [{"role": "user", "content": "2"}]})
    sc = client.get("/_agentbreak/scorecard").json()
    assert sc["run_outcome"] == "FAIL"
    assert sc["resilience_score"] < 100
    assert sc["injected_faults"] == 2
    assert sc["upstream_failures"] == 2


def test_llm_duplicate_and_loop_detection():
    main.service_state.llm_runtime = _make_runtime()
    client = TestClient(main.app)
    body = {"model": "m", "messages": [{"role": "user", "content": "same"}]}
    client.post("/v1/chat/completions", json=body)
    client.post("/v1/chat/completions", json=body)
    client.post("/v1/chat/completions", json=body)
    sc = client.get("/_agentbreak/scorecard").json()
    assert sc["duplicate_requests"] >= 2
    assert sc["suspected_loops"] >= 1


# ── Disabled / requests endpoint ─────────────────────────────────────


def test_llm_disabled_returns_404():
    main.service_state.llm_runtime = None
    client = TestClient(main.app)
    r = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert r.status_code == 404


def test_llm_requests_endpoint():
    main.service_state.llm_runtime = _make_runtime()
    client = TestClient(main.app)
    client.post("/v1/chat/completions", json=CHAT_BODY)
    r = client.get("/_agentbreak/requests").json()
    assert len(r["recent_requests"]) == 1
    assert "fingerprint" in r["recent_requests"][0]
