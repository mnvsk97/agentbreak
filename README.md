# AgentBreak

Chaos proxy for testing how your agents handle failures. Sits between your agent and the LLM/MCP server, injects faults.

```
Agent  -->  AgentBreak (localhost:5005)  -->  Real LLM / MCP server
                     ^
          .agentbreak/scenarios.yaml defines faults
```

## Quick start

```bash
pip install agentbreak
agentbreak init       # creates .agentbreak/ with default configs
agentbreak serve      # start the chaos proxy
```

Point your agent at `http://localhost:5005` instead of the real API:

- OpenAI SDK: set `OPENAI_BASE_URL=http://localhost:5005/v1`
- Anthropic SDK: set `ANTHROPIC_BASE_URL=http://localhost:5005`

Check results:

```bash
curl localhost:5005/_agentbreak/scorecard
```

## Config

**`.agentbreak/application.yaml`** -- what to proxy:

```yaml
llm:
  enabled: true
  mode: mock           # mock (no API key needed) or proxy (forwards to upstream)
mcp:
  enabled: false       # set true + upstream_url for MCP testing
serve:
  port: 5005
```

**`.agentbreak/scenarios.yaml`** -- what faults to inject:

```yaml
version: 1
scenarios:
  - name: slow-llm
    summary: Latency spike on completions
    target: llm_chat
    fault:
      kind: latency
      min_ms: 2000
      max_ms: 5000
    schedule:
      mode: random
      probability: 0.3
```

Or use a preset: `brownout`, `mcp-slow-tools`, `mcp-tool-failures`, `mcp-mixed-transient`.

## Writing your own scenarios

Each scenario has a **target**, a **fault**, and a **schedule**. You can add as many as you want to `scenarios.yaml`.

### Targets

| Target | What it hits |
|--------|-------------|
| `llm_chat` | OpenAI `/v1/chat/completions` and Anthropic `/v1/messages` |
| `mcp_tool` | MCP tool calls, resource reads, prompt gets |

### Fault kinds

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

### Schedules

| Mode | Fields | Behavior |
|------|--------|----------|
| `always` | -- | Every matching request |
| `random` | `probability` (0.0-1.0) | Probabilistic |
| `periodic` | `every`, `length` | `length` faults every `every` requests |

### Targeting specific tools or models

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

### Presets

Skip manual config and use a built-in bundle:

```yaml
preset: brownout
# or combine a preset with custom scenarios:
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

## MCP testing

```bash
agentbreak inspect    # discover tools from upstream MCP server
agentbreak serve      # proxy both LLM and MCP traffic
```

## Run history

Track resilience over time:

```yaml
# in .agentbreak/application.yaml
history:
  enabled: true
```

```bash
agentbreak serve --label "added retry logic"
# ... run your agent ...
agentbreak history                    # list past runs
agentbreak history compare 1 2        # diff two runs
```

## CLI

```bash
agentbreak init       # create .agentbreak/ config
agentbreak serve      # start proxy
agentbreak validate   # check config
agentbreak inspect    # discover MCP tools
agentbreak verify     # run tests
agentbreak history    # view past runs
```

## Claude Code

If you use [Claude Code](https://docs.anthropic.com/en/docs/claude-code), you can run AgentBreak as a guided skill instead of using the CLI directly:

```bash
npx skills add mnvsk97/agentbreak
```

Then type `/agentbreak` in Claude Code. The skill will scan your codebase, detect your LLM provider and MCP tools, generate tailored chaos scenarios, start the proxy, and walk you through interpreting the results.

## Examples

See [examples/](examples/) for sample agents and MCP servers with various auth configs.
