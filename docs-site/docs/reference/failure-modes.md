# Failure Modes

What AgentBreak simulates — and what's out of scope.

## Targets

- `llm_chat` — OpenAI (`/v1/chat/completions`) and Anthropic (`/v1/messages`) chat APIs
- `mcp_tool` — MCP tool calls, resource reads, prompt gets

## Fault support matrix

| Fault | LLM | MCP | Notes |
|-------|-----|-----|-------|
| `http_error` | yes | yes | Requires `status_code` |
| `latency` | yes | yes | Requires `min_ms`, `max_ms` |
| `timeout` | no | yes | Requires `min_ms`, `max_ms`; sleeps then returns 504 |
| `empty_response` | yes | yes | |
| `invalid_json` | yes | yes | |
| `schema_violation` | yes | yes | Corrupts tool_calls (LLM) or result shape (MCP) |
| `wrong_content` | yes | yes | Optional `body` field |
| `large_response` | yes | yes | Requires `size_bytes` > 0 |

## Built-in behavioral detection

- **Duplicate request detection** — fingerprint-based, for both LLM and MCP
- **Suspected loop detection** — 3+ identical requests
- **Expired upstream MCP session recovery** — re-initializes on session errors

## Out of scope (for now)

- Prompt injection
- Memory poisoning
- Queue replay
- Checkpoint corruption
- Browser worker failures
- Multi-agent coordination failures

See [Roadmap](../roadmap.md) for planned future targets.
