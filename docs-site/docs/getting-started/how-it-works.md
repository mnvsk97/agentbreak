# How It Works

AgentBreak is a transparent proxy. It sits between your agent and the services it depends on, intercepting traffic and injecting controlled faults.

```
Agent  →  AgentBreak (localhost:5005)  →  Upstream LLM / MCP
               ↑
         scenarios.yaml (fault rules)
```

The agent talks to AgentBreak as if it were the real service. AgentBreak either forwards to the real upstream (**proxy mode**) or returns synthetic responses (**mock mode**), optionally corrupting, delaying, or replacing responses along the way.

## Supported API formats

AgentBreak exposes three endpoints, all backed by the same fault injection engine:

| Endpoint | Format |
|----------|--------|
| `POST /v1/chat/completions` | OpenAI |
| `POST /v1/messages` | Anthropic Messages |
| `POST /mcp` | MCP (JSON-RPC over HTTP) |

## What gets tested

AgentBreak focuses on **infrastructure-level** failures, not semantic attacks. The goal is to answer: *"Does my agent handle real-world service degradation gracefully?"*

| Category | What it simulates | Example |
|----------|-------------------|---------|
| **Availability** | Service outages, rate limits | `http_error` with status 503 or 429 |
| **Latency** | Slow responses, network delays | `latency` with min/max milliseconds |
| **Timeouts** | Requests that never complete | `timeout` with min/max milliseconds |
| **Corruption** | Broken payloads | `invalid_json`, `empty_response`, `schema_violation` |
| **Content drift** | Unexpected response content | `wrong_content`, `large_response` |

## Behavioral detection

Beyond injected faults, AgentBreak passively monitors:

- **Duplicate requests** — same payload sent more than once (fingerprint-based)
- **Suspected loops** — same payload sent 3+ times, indicating the agent is stuck
- **Upstream failures** — real errors from the upstream service (not injected)

## Scoring

After a run, the scorecard gives you:

- **Resilience score** (0-100) — starts at 100, deductions for faults, failures, duplicates, and loops
- **Run outcome** — `PASS` (clean), `DEGRADED` (partial failures), or `FAIL` (all failed or looping)

| Deduction | Amount |
|-----------|--------|
| Per injected fault | -3 |
| Per upstream failure | -12 |
| Per duplicate request | -2 |
| Per suspected loop | -10 |
