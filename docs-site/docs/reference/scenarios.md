# Scenarios Reference

Each scenario in `.agentbreak/scenarios.yaml` has a **target**, a **fault**, and a **schedule**.

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
| `empty_response` | Returns empty body | — |
| `invalid_json` | Returns unparseable JSON | — |
| `schema_violation` | Corrupts response structure | — |
| `wrong_content` | Replaces response content | `body` (optional) |
| `large_response` | Returns oversized response | `size_bytes` |

## Schedules

| Mode | Fields | Behavior |
|------|--------|----------|
| `always` | — | Every matching request |
| `random` | `probability` (0.0-1.0) | Probabilistic |
| `periodic` | `every`, `length` | `length` faults every `every` requests |

## Match filters

Use the `match` field to scope faults to specific models or tools.

### By model

```yaml
match:
  model: gpt-4o
```

### By tool name

```yaml
match:
  tool_name: search_docs
```

### By tool name pattern (wildcard)

```yaml
match:
  tool_name_pattern: "search_*"
```

## Full example

```yaml
scenarios:
  - name: gpt4o-rate-limits
    summary: Rate limits on GPT-4o only
    target: llm_chat
    match:
      model: gpt-4o
    fault:
      kind: http_error
      status_code: 429
    schedule:
      mode: random
      probability: 0.3

  - name: search-timeout
    summary: search_docs always times out
    target: mcp_tool
    match:
      tool_name: search_docs
    fault:
      kind: timeout
      min_ms: 5000
      max_ms: 10000
    schedule:
      mode: always
```

## Presets

Skip manual config with built-in bundles:

```yaml
preset: brownout
```

Combine a preset with custom scenarios:

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

| Preset | What it does |
|--------|-------------|
| `brownout` | Random LLM latency + rate limits |
| `mcp-slow-tools` | 90% of MCP tool calls are slow |
| `mcp-tool-failures` | 30% of MCP tool calls return 503 |
| `mcp-mixed-transient` | Light MCP latency + errors |
