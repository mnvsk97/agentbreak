# MCP Testing

AgentBreak can proxy and fault-inject MCP (Model Context Protocol) traffic alongside LLM calls.

## Setup

### 1. Enable MCP in config

```yaml
# .agentbreak/application.yaml
mcp:
  enabled: true
  upstream_url: http://localhost:3000/mcp   # your MCP server
```

### 2. Discover tools

```bash
agentbreak inspect
```

This connects to your MCP server, discovers available tools, resources, and prompts, and writes the registry to `.agentbreak/registry.json`.

### 3. Write MCP scenarios

Target MCP traffic with `target: mcp_tool`:

```yaml
scenarios:
  - name: slow-tools
    summary: MCP tool calls are slow
    target: mcp_tool
    fault:
      kind: latency
      min_ms: 3000
      max_ms: 8000
    schedule:
      mode: random
      probability: 0.5
```

### 4. Start the proxy

```bash
agentbreak serve
```

MCP traffic goes through `POST /mcp`.

## Targeting specific tools

Use `match` to scope faults to specific tools:

```yaml
# Single tool
match:
  tool_name: search_docs

# Wildcard pattern
match:
  tool_name_pattern: "search_*"
```

## MCP-specific faults

| Fault | Behavior |
|-------|----------|
| `timeout` | Delays the response, then returns 504 (MCP only) |
| `http_error` | Returns an HTTP error for the tool call |
| `empty_response` | Returns an empty result |
| `schema_violation` | Corrupts the result shape |

## MCP scorecard

MCP has its own scorecard endpoint:

```bash
curl localhost:5005/_agentbreak/mcp-scorecard
curl localhost:5005/_agentbreak/mcp-requests
```

## Presets for MCP

| Preset | What it does |
|--------|-------------|
| `mcp-slow-tools` | 90% of MCP tool calls are slow |
| `mcp-tool-failures` | 30% of MCP tool calls return 503 |
| `mcp-mixed-transient` | Light MCP latency + errors |
