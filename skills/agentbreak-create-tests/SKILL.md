---
name: agentbreak-create-tests
description: Generate chaos test scenarios for AgentBreak. Produces scenarios.yaml entries that conform to the Pydantic schema, target LLM chat completions and MCP tool calls, and integrate with application.yaml.
---

# AgentBreak -- Create Tests

Use this skill to generate `scenarios.yaml` entries for AgentBreak chaos testing.

## What you're creating

A `scenarios.yaml` file that AgentBreak reads at startup. Each scenario defines one fault injected into one target (LLM or MCP) on a schedule. The file is validated against Pydantic models in `agentbreak/scenarios.py` at load time.

## Step by step

1. Understand the user's agent: what LLM provider, what MCP tools, what breaks in production?
2. Write scenarios targeting those specific surfaces
3. Write or update `scenarios.yaml`
4. Validate: `agentbreak validate --config application.yaml --scenarios scenarios.yaml`
5. The user runs `agentbreak serve` and points their agent at the proxy

## Pydantic schema

Every scenario must conform to these models (defined in `agentbreak/scenarios.py`):

### ScenarioFile (top level)

```yaml
version: 1          # always 1
scenarios: [...]     # list of Scenario objects
```

Can also include `preset: <name>` or `presets: [...]` to expand built-in templates.

### Scenario

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | yes | Unique, descriptive, kebab-case |
| `summary` | string | yes | One-line description of the failure |
| `target` | string | yes | `llm_chat` or `mcp_tool` (only these two are implemented) |
| `match` | MatchSpec | no | Defaults to match everything |
| `fault` | FaultSpec | yes | What fault to inject |
| `schedule` | ScheduleSpec | no | Defaults to `mode: always` |
| `tags` | list[string] | no | Optional labels |

### MatchSpec (all fields optional, all must match if set)

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `tool_name` | string | `search_docs` | Exact match on MCP tool name |
| `tool_name_pattern` | string | `search_*` | Glob pattern (fnmatch) |
| `route` | string | `/v1/chat/completions` | Request path |
| `method` | string | `tools/call` | MCP method or HTTP method |
| `model` | string | `gpt-4o` | LLM model name |

### FaultSpec

| Field | Type | Required for | Validation |
|-------|------|-------------|------------|
| `kind` | string | always | One of the 8 fault kinds below |
| `status_code` | int | `http_error` | Must be set for http_error |
| `min_ms` | int | `latency`, `timeout` | >= 0, must be <= max_ms |
| `max_ms` | int | `latency`, `timeout` | >= 0, must be >= min_ms |
| `size_bytes` | int | `large_response` | Must be > 0 |
| `body` | string | optional for `wrong_content` | Custom response body |

**Fault kinds:**

| Kind | Extra fields | Target restriction |
|------|-------------|-------------------|
| `http_error` | `status_code` (required) | llm_chat, mcp_tool |
| `latency` | `min_ms`, `max_ms` (required) | llm_chat, mcp_tool |
| `timeout` | `min_ms`, `max_ms` (required) | **mcp_tool only** (rejected for llm_chat) |
| `empty_response` | none | llm_chat, mcp_tool |
| `invalid_json` | none | llm_chat, mcp_tool |
| `schema_violation` | none | llm_chat, mcp_tool |
| `wrong_content` | `body` (optional) | llm_chat, mcp_tool |
| `large_response` | `size_bytes` (required, > 0) | llm_chat, mcp_tool |

### ScheduleSpec

| Field | Type | Required for | Validation |
|-------|------|-------------|------------|
| `mode` | string | always | `always`, `random`, or `periodic` |
| `probability` | float | `random` | 0.0 to 1.0 |
| `every` | int | `periodic` | > 0 |
| `length` | int | `periodic` | > 0, must be <= `every` |

## Connecting to application.yaml

Scenarios don't run in isolation. They need a matching `application.yaml`:

- **LLM scenarios** (`target: llm_chat`) require `llm.enabled: true` in application.yaml. Set `llm.mode: mock` for testing without an API key, or `llm.mode: proxy` with `llm.upstream_url` to test against a real provider.

- **MCP scenarios** (`target: mcp_tool`) require `mcp.enabled: true` and `mcp.upstream_url` in application.yaml. Also requires running `agentbreak inspect` first to generate `.agentbreak/registry.json`.

- Both can be enabled at once for mixed LLM + MCP testing.

Minimal application.yaml for LLM-only testing:

```yaml
llm:
  enabled: true
  mode: mock
mcp:
  enabled: false
serve:
  port: 5000
```

Minimal application.yaml for MCP testing:

```yaml
llm:
  enabled: false
mcp:
  enabled: true
  upstream_url: http://localhost:8080/mcp
  auth:
    type: bearer
    env: MCP_API_KEY
serve:
  port: 5000
```

Note: MCP-targeted scenarios are silently ignored when `mcp.enabled: false`. If you write scenarios with `target: mcp_tool`, make sure MCP is enabled in application.yaml or they will never fire.

## Presets

For quick coverage, use a preset instead of writing scenarios by hand:

```yaml
version: 1
preset: brownout
```

| Preset | Target | Scenarios |
|--------|--------|-----------|
| `brownout` | llm_chat | Random latency (p=0.2) + random 429s (p=0.3) |
| `mcp-slow-tools` | mcp_tool | Random latency (p=0.9) |
| `mcp-tool-failures` | mcp_tool | Random 503s (p=0.3) |
| `mcp-mixed-transient` | mcp_tool | Random latency (p=0.1) + random 503s (p=0.2) |

Presets can be combined with explicit scenarios:

```yaml
version: 1
preset: brownout
scenarios:
  - name: search-timeout
    summary: Search tool times out
    target: mcp_tool
    match:
      tool_name: search_docs
    fault:
      kind: timeout
      min_ms: 30000
      max_ms: 60000
    schedule:
      mode: random
      probability: 0.2
```

## Writing good scenarios

1. **Ask what the user worries about.** "What fails in production?" or "What would break your agent?"

2. **Target specific tools/models.** `match: {}` is fine for broad testing, but `tool_name: search_docs` catches issues in specific integrations.

3. **Use realistic probabilities.** 0.1-0.3 simulates real intermittent failures. Use `mode: always` only when debugging a specific fault path.

4. **Cover multiple fault kinds.** A good suite includes at least: one HTTP error (429 or 500), one latency spike, and one response mutation (invalid_json or schema_violation).

5. **Name clearly.** `search-tool-timeout` is better than `test-1`.

6. **Remember: `timeout` is MCP only.** Using `timeout` with `target: llm_chat` will fail validation.

## Example: RAG agent with search and fetch tools

```yaml
version: 1
scenarios:
  - name: search-rate-limited
    summary: Search API returns 429
    target: mcp_tool
    match:
      tool_name: search_docs
    fault:
      kind: http_error
      status_code: 429
    schedule:
      mode: random
      probability: 0.2

  - name: search-slow
    summary: Search takes 10-30 seconds
    target: mcp_tool
    match:
      tool_name: search_docs
    fault:
      kind: latency
      min_ms: 10000
      max_ms: 30000
    schedule:
      mode: random
      probability: 0.3

  - name: fetch-returns-garbage
    summary: Page fetch returns invalid JSON
    target: mcp_tool
    match:
      tool_name: fetch_page
    fault:
      kind: invalid_json
    schedule:
      mode: random
      probability: 0.15

  - name: llm-server-error
    summary: LLM returns 500 intermittently
    target: llm_chat
    fault:
      kind: http_error
      status_code: 500
    schedule:
      mode: random
      probability: 0.1

  - name: llm-wrong-content
    summary: LLM returns irrelevant content
    target: llm_chat
    fault:
      kind: wrong_content
      body: "I don't know how to help with that."
    schedule:
      mode: periodic
      every: 10
      length: 1
```

## Validation

Always validate before serving:

```bash
agentbreak validate --config application.yaml --scenarios scenarios.yaml
```

This catches:
- Invalid fault kinds or missing required fields
- Unsupported targets (e.g., `queue`, `state` -- recognized but not implemented)
- `timeout` used with `llm_chat`
- Schedule constraint violations (probability out of range, length > every)
- Missing `llm.upstream_url` when `llm.mode: proxy`

## After creating scenarios

```bash
agentbreak validate --config application.yaml --scenarios scenarios.yaml
agentbreak serve --config application.yaml --scenarios scenarios.yaml
# Point agent at http://localhost:5000/v1 (LLM) or http://localhost:5000/mcp (MCP)
# Check results: curl http://localhost:5000/_agentbreak/scorecard
```
