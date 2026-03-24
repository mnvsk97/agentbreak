from agentbreak.scenarios import MatchSpec, FaultSpec, ScheduleSpec, Scenario, ScenarioFile, load_scenarios, PRESET_SCENARIOS
from agentbreak.main import choose_matching_scenario, should_apply_scenario
import pytest

# MatchSpec tests
def test_match_empty_matches_everything():
    m = MatchSpec()
    assert m.matches({"tool_name": "x", "route": "/v1", "method": "POST", "model": "gpt-4o"})

def test_match_tool_name_exact():
    m = MatchSpec(tool_name="search")
    assert m.matches({"tool_name": "search"})
    assert not m.matches({"tool_name": "fetch"})

def test_match_tool_name_pattern():
    m = MatchSpec(tool_name_pattern="search_*")
    assert m.matches({"tool_name": "search_docs"})
    assert m.matches({"tool_name": "search_notes"})
    assert not m.matches({"tool_name": "fetch_docs"})

def test_match_route():
    m = MatchSpec(route="/v1/chat/completions")
    assert m.matches({"route": "/v1/chat/completions"})
    assert not m.matches({"route": "/v1/embeddings"})

def test_match_model():
    m = MatchSpec(model="gpt-4o")
    assert m.matches({"model": "gpt-4o"})
    assert not m.matches({"model": "gpt-3.5"})

def test_match_multiple_fields_all_must_match():
    m = MatchSpec(tool_name="search", method="tools/call")
    assert m.matches({"tool_name": "search", "method": "tools/call"})
    assert not m.matches({"tool_name": "search", "method": "resources/read"})
    assert not m.matches({"tool_name": "other", "method": "tools/call"})

# Schedule tests
def test_schedule_always():
    assert should_apply_scenario(Scenario(name="x", summary="x", target="llm_chat", fault=FaultSpec(kind="empty_response"), schedule=ScheduleSpec(mode="always")), 1)
    assert should_apply_scenario(Scenario(name="x", summary="x", target="llm_chat", fault=FaultSpec(kind="empty_response"), schedule=ScheduleSpec(mode="always")), 100)

def test_schedule_periodic():
    s = Scenario(name="x", summary="x", target="llm_chat", fault=FaultSpec(kind="empty_response"), schedule=ScheduleSpec(mode="periodic", every=5, length=2))
    results = [should_apply_scenario(s, i) for i in range(1, 11)]
    # every=5, length=2: requests 1,2 fire, 3,4,5 don't, 6,7 fire, 8,9,10 don't
    assert results == [True, True, False, False, False, True, True, False, False, False]

def test_schedule_random_probability_zero():
    s = Scenario(name="x", summary="x", target="llm_chat", fault=FaultSpec(kind="empty_response"), schedule=ScheduleSpec(mode="random", probability=0.0))
    # With p=0, should never fire
    assert all(not should_apply_scenario(s, i) for i in range(1, 100))

def test_schedule_random_probability_one():
    s = Scenario(name="x", summary="x", target="llm_chat", fault=FaultSpec(kind="empty_response"), schedule=ScheduleSpec(mode="random", probability=1.0))
    # With p=1, should always fire
    assert all(should_apply_scenario(s, i) for i in range(1, 100))

# choose_matching_scenario tests
def test_choose_skips_wrong_target():
    scenarios = ScenarioFile.model_validate({"scenarios": [
        {"name": "mcp-only", "summary": "x", "target": "mcp_tool", "fault": {"kind": "empty_response"}, "schedule": {"mode": "always"}}
    ]}).scenarios
    result = choose_matching_scenario(scenarios, "llm_chat", {"route": "/v1"}, {})
    assert result is None

def test_choose_matches_correct_target():
    scenarios = ScenarioFile.model_validate({"scenarios": [
        {"name": "llm", "summary": "x", "target": "llm_chat", "fault": {"kind": "empty_response"}, "schedule": {"mode": "always"}}
    ]}).scenarios
    result = choose_matching_scenario(scenarios, "llm_chat", {"route": "/v1"}, {})
    assert result is not None
    assert result.name == "llm"

def test_choose_respects_match_filter():
    scenarios = ScenarioFile.model_validate({"scenarios": [
        {"name": "gpt4-only", "summary": "x", "target": "llm_chat", "match": {"model": "gpt-4o"}, "fault": {"kind": "empty_response"}, "schedule": {"mode": "always"}}
    ]}).scenarios
    assert choose_matching_scenario(scenarios, "llm_chat", {"model": "gpt-4o"}, {}) is not None
    assert choose_matching_scenario(scenarios, "llm_chat", {"model": "gpt-3.5"}, {}) is None

def test_choose_increments_counters():
    scenarios = ScenarioFile.model_validate({"scenarios": [
        {"name": "s1", "summary": "x", "target": "llm_chat", "fault": {"kind": "empty_response"}, "schedule": {"mode": "always"}}
    ]}).scenarios
    counters = {}
    choose_matching_scenario(scenarios, "llm_chat", {}, counters)
    choose_matching_scenario(scenarios, "llm_chat", {}, counters)
    assert counters["s1"] == 2

# Validation tests
def test_fault_http_error_requires_status_code():
    with pytest.raises(Exception):
        FaultSpec(kind="http_error")

def test_fault_latency_requires_bounds():
    with pytest.raises(Exception):
        FaultSpec(kind="latency")
    with pytest.raises(Exception):
        FaultSpec(kind="latency", min_ms=10)

def test_fault_latency_rejects_invalid_bounds():
    with pytest.raises(Exception):
        FaultSpec(kind="latency", min_ms=100, max_ms=50)

def test_fault_large_response_requires_size():
    with pytest.raises(Exception):
        FaultSpec(kind="large_response")
    with pytest.raises(Exception):
        FaultSpec(kind="large_response", size_bytes=0)

def test_schedule_random_rejects_invalid_probability():
    with pytest.raises(Exception):
        ScheduleSpec(mode="random", probability=1.5)

def test_schedule_periodic_requires_every_and_length():
    with pytest.raises(Exception):
        ScheduleSpec(mode="periodic")
    with pytest.raises(Exception):
        ScheduleSpec(mode="periodic", every=5)

def test_schedule_periodic_length_cannot_exceed_every():
    with pytest.raises(Exception):
        ScheduleSpec(mode="periodic", every=3, length=5)

# Preset tests
def test_all_presets_are_valid():
    for name, entries in PRESET_SCENARIOS.items():
        sf = ScenarioFile.model_validate({"scenarios": entries})
        assert len(sf.scenarios) > 0, f"Preset {name} is empty"

def test_load_scenarios_missing_file_returns_empty():
    sf = load_scenarios("/nonexistent/path/scenarios.yaml")
    assert sf.scenarios == []
