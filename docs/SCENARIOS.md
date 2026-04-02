# Scenario Reference

Each scenario in `.agentbreak/scenarios.yaml` has a **target**, a **fault**, and a **schedule**. You can add as many as you want.

## Targets

| Target | What it hits |
|--------|-------------|
| `llm_chat` | OpenAI `/v1/chat/completions` and Anthropic `/v1/messages` |
| `mcp_tool` | MCP tool calls, resource reads, prompt gets |

## Fault kinds

| Fault | What it does | Required fields |
|-------|-------------|-----------------|
| `http_error` | Returns an HTTP error | `status_code` |
| `latency` | Adds a random delay | `min_ms`, `max_ms` |
| `timeout` | Delay + 504 (MCP only) | `min_ms`, `max_ms` |
| `empty_response` | Returns empty body | -- |
| `invalid_json` | Returns unparseable JSON | -- |
| `schema_violation` | Corrupts response structure | -- |
| `wrong_content` | Replaces response content | `body` (optional) |
| `large_response` | Returns oversized response | `size_bytes` |

## Schedules

| Mode | Fields | Behavior |
|------|--------|----------|
| `always` | -- | Every matching request |
| `random` | `probability` (0.0-1.0) | Probabilistic |
| `periodic` | `every`, `length` | `length` faults every `every` requests |

## Targeting specific tools or models

Use the `match` field to scope faults:

```yaml
# Only affect GPT-4o requests
- name: gpt4o-errors
  summary: Errors on GPT-4o only
  target: llm_chat
  match:
    model: gpt-4o
  fault:
    kind: http_error
    status_code: 429
  schedule:
    mode: random
    probability: 0.3

# Only affect a specific MCP tool
- name: search-timeout
  summary: search_docs times out
  target: mcp_tool
  match:
    tool_name: search_docs
  fault:
    kind: timeout
    min_ms: 5000
    max_ms: 10000
  schedule:
    mode: always

# Wildcard match on tool names
- name: search-tools-slow
  summary: All search_* tools are slow
  target: mcp_tool
  match:
    tool_name_pattern: "search_*"
  fault:
    kind: latency
    min_ms: 3000
    max_ms: 8000
  schedule:
    mode: random
    probability: 0.5
```

## Presets

Skip manual config and use a built-in bundle:

```yaml
preset: brownout
```

Or combine a preset with custom scenarios:

```yaml
preset: brownout
scenarios:
  - name: custom-fault
    summary: My extra fault
    target: mcp_tool
    fault:
      kind: http_error
      status_code: 503
    schedule:
      mode: random
      probability: 0.2
```

Available presets: `brownout`, `mcp-slow-tools`, `mcp-tool-failures`, `mcp-mixed-transient`.
