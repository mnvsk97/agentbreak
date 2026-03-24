---
name: agentbreak
description: Test an LLM or MCP app with AgentBreak -- configure application.yaml and scenarios.yaml, serve/inspect/validate/verify, point clients at the proxy, read scorecards.
---

# AgentBreak

AgentBreak is a chaos proxy for OpenAI-compatible chat completions and MCP over streamable HTTP. It injects faults defined in `scenarios.yaml` according to `application.yaml`.

## How it works

```text
Your app --> AgentBreak --> (mock LLM | real upstream LLM)
                        --> (mirrored MCP | injected MCP faults)
```

- `llm.mode: mock` -- synthetic completions unless a scenario injects a fault. No API key needed.
- `llm.mode: proxy` -- forwards `/v1/chat/completions` to `llm.upstream_url` when no fault fires.
- `mcp.enabled: true` -- run `agentbreak inspect` once to write `.agentbreak/registry.json`, then `serve` mirrors MCP through AgentBreak.

## Quick start

```bash
pip install agentbreak   # or: pip install -e '.[dev]' from repo root

cp config.example.yaml application.yaml
cp scenarios.example.yaml scenarios.yaml
# Edit application.yaml: set llm.mode, mcp.enabled, upstreams, auth

agentbreak serve --config application.yaml --scenarios scenarios.yaml
```

Point clients at:

```bash
export OPENAI_BASE_URL=http://127.0.0.1:5000/v1
export OPENAI_API_KEY=dummy   # mock mode; use a real key in proxy mode
```

## CLI commands

| Command | Purpose |
|---------|---------|
| `serve` | Run the proxy (`--config`, `--scenarios`, `--registry`, `--verbose/-v`) |
| `validate` | Check config + scenarios + registry without starting the server |
| `inspect` | Discover upstream MCP tools/resources/prompts; write registry (`mcp.enabled` must be true) |
| `verify` | Run pytest; add `--live` for the full LangGraph + mock OpenAI + MCP harness |

There is no `agentbreak start`. Scenarios live in `scenarios.yaml`, not CLI flags. Config file must exist or `serve`/`validate` will raise `FileNotFoundError`.

## Scenario format

Each scenario targets `llm_chat` or `mcp_tool`, declares a fault, and a schedule.

```yaml
version: 1
scenarios:
  - name: flaky-llm
    summary: Random 429s
    target: llm_chat
    match:
      model: gpt-4o
    fault:
      kind: http_error
      status_code: 429
    schedule:
      mode: random
      probability: 0.3
```

Fault kinds: `http_error`, `latency`, `timeout`, `empty_response`, `invalid_json`, `schema_violation`, `wrong_content`, `large_response`.

Schedule modes: `always`, `random` (with `probability`), `periodic` (with `every` and `length`).

Match fields (all optional): `tool_name`, `tool_name_pattern` (glob), `route`, `method`, `model`.

Presets (use `preset: <name>` instead of writing scenarios by hand): `brownout`, `mcp-slow-tools`, `mcp-tool-failures`, `mcp-mixed-transient`.

## Endpoints

```bash
curl http://127.0.0.1:5000/healthz

# LLM (/_agentbreak/scorecard and /_agentbreak/requests are aliases for llm-)
curl http://127.0.0.1:5000/_agentbreak/llm-scorecard
curl http://127.0.0.1:5000/_agentbreak/llm-requests

# MCP
curl http://127.0.0.1:5000/_agentbreak/mcp-scorecard
curl http://127.0.0.1:5000/_agentbreak/mcp-requests
```

Ctrl+C prints a resilience scorecard summary to stderr.

## LLM scorecard fields

`requests_seen`, `injected_faults`, `latency_injections`, `upstream_successes`, `upstream_failures`, `duplicate_requests`, `suspected_loops`, `run_outcome` (PASS/DEGRADED/FAIL), `resilience_score` (0-100).

## MCP scorecard fields

All the above plus: `tool_calls`, `method_counts`, `tool_call_counts`, `tool_successes_by_name`, `tool_failures_by_name`, `response_mutations`.

Treat duplicate/loop counters as signals -- some frameworks legitimately repeat requests.

## Debugging

- `OPENAI_BASE_URL` must include `/v1` for OpenAI-compatible clients.
- Mock LLM: any non-empty `OPENAI_API_KEY` works (e.g. `dummy`).
- Proxy LLM: verify `upstream_url`, auth env vars, and network to the provider.
- MCP: ensure `inspect` ran and `.agentbreak/registry.json` exists before `serve`.

## Verification

```bash
agentbreak verify
agentbreak verify --live   # full stack
```

## References

- `README.md` -- scenario format, examples, scope
- `CONTRIBUTING.md` -- dev install and commands
- `skills/agentbreak-run-tests/SKILL.md` -- run chaos tests
- `skills/agentbreak-create-tests/SKILL.md` -- generate chaos scenarios
