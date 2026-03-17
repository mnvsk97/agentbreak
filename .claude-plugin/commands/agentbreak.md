---
name: agentbreak
description: Use when testing an LLM app with AgentBreak — start the server, choose a scenario, run the app, and interpret the scorecard.
---

# AgentBreak

AgentBreak is a chaos proxy for OpenAI-compatible LLM apps. It sits between your app and the provider and randomly injects faults, latency, or fake responses so you can verify your app retries correctly, falls back gracefully, and does not loop.

## Mental Model

```
mock mode:   your app → AgentBreak → fake response (or injected fault)
proxy mode:  your app → AgentBreak → real upstream (or injected fault)
```

In **mock mode** every un-faulted request returns a static success response. No real upstream is needed. Use this for local development and CI.

In **proxy mode** un-faulted requests are forwarded to the real upstream. Use this for end-to-end resilience testing against a live provider.

## Quick Start

```bash
pip install agentbreak

# mock mode — no upstream needed
agentbreak start --mode mock --scenario mixed-transient --fail-rate 0.2

# point your app at it
export OPENAI_BASE_URL=http://localhost:5000/v1
export OPENAI_API_KEY=dummy
```

## Modes

| Mode    | When to use                                                      |
|---------|------------------------------------------------------------------|
| `mock`  | Local dev, CI pipelines, no upstream credentials needed          |
| `proxy` | End-to-end resilience testing with a real provider               |

Proxy mode requires `--upstream-url`:

```bash
agentbreak start \
  --mode proxy \
  --upstream-url https://api.openai.com \
  --scenario mixed-transient \
  --fail-rate 0.2
```

In proxy mode use a real API key, not `dummy`.

## Scenarios

Scenarios are named presets for which error codes get injected. Pass one with `--scenario`.

| Scenario           | Injected codes          | Latency | What it tests                                  |
|--------------------|-------------------------|---------|------------------------------------------------|
| `mixed-transient`  | 429, 500, 503           | none    | General retry + backoff logic (default)        |
| `rate-limited`     | 429 only                | none    | Rate limit handling and backoff                |
| `provider-flaky`   | 500, 503                | none    | Server error recovery                          |
| `non-retryable`    | 400, 401, 403, 404, 413 | none    | Whether the app stops retrying on hard errors  |
| `brownout`         | 429, 500, 503           | 20%     | Degraded performance with mixed errors         |

The scenario determines which codes are randomly selected when a fault fires. `--fail-rate` controls how often a fault fires at all.

## Fail Rate vs Weighted Faults

**`--fail-rate`** (simple): probability that any given request gets a fault. The code is chosen randomly from the scenario's error codes.

```bash
agentbreak start --mode mock --scenario mixed-transient --fail-rate 0.3
# 30% of requests get a fault (429, 500, or 503 chosen at random)
```

**`--faults`** (precise): exact probability per code. Overrides `--fail-rate` and `--scenario` for fault selection. The total must be ≤ 1.0 — the remainder are pass-throughs.

```bash
agentbreak start --mode mock --faults 500=0.3,429=0.2
# 30% → 500, 20% → 429, 50% → success
```

Supported error codes: `400 401 403 404 413 429 500 503`

## Latency Injection

`--latency-p` is the probability of adding a delay to a non-faulted request. `--latency-min` and `--latency-max` set the range in **seconds** (not milliseconds).

```bash
agentbreak start --mode mock --scenario brownout --latency-p 0.4 --latency-min 3 --latency-max 10
```

The `brownout` scenario already sets `latency-p 0.2` by default.

## CLI Reference

```
agentbreak start [OPTIONS]

  --config PATH           YAML config file (default: ./config.yaml if present)
  --mode TEXT             proxy | mock
  --upstream-url TEXT     Base URL without /v1 (required in proxy mode)
  --scenario TEXT         Built-in scenario name (see table above)
  --fail-rate FLOAT       0.0–1.0 probability of injecting a fault
  --faults TEXT           Per-code rates, e.g. 500=0.3,429=0.2
  --error-codes TEXT      Comma-separated codes to use instead of scenario defaults
  --latency-p FLOAT       Probability of injecting latency on non-faulted requests
  --latency-min FLOAT     Min delay in seconds (default 5)
  --latency-max FLOAT     Max delay in seconds (default 15)
  --seed INT              Fix random seed for deterministic runs
  --port INT              Port to bind on (default 5000)
```

CLI flags override config file values.

## Config File

AgentBreak auto-loads `config.yaml` from the current directory. Copy the example to get started:

```bash
cp config.example.yaml config.yaml
agentbreak start
```

Full config reference:

```yaml
mode: proxy                        # proxy | mock
upstream_url: https://api.openai.com
scenario: mixed-transient
fail_rate: 0.2

# Latency injection
latency_p: 0.0                     # probability of adding delay to non-faulted requests
latency_min: 5                     # seconds
latency_max: 15                    # seconds

request_count: 10                  # used by example scripts (not the server itself)

# Advanced: exact per-code rates (overrides fail_rate if set)
faults:
  "500": 0.3
  "429": 0.2
```

## Useful Endpoints

```bash
# Summary of what happened
curl http://localhost:5000/_agentbreak/scorecard

# Last 20 requests with fingerprints and bodies
curl http://localhost:5000/_agentbreak/requests

# Health check
curl http://localhost:5000/healthz
```

Stop the server with `Ctrl+C` to print the final scorecard in the terminal.

## Scorecard Reference

```json
{
  "requests_seen": 10,
  "injected_faults": 2,
  "latency_injections": 0,
  "upstream_successes": 8,
  "upstream_failures": 2,
  "duplicate_requests": 0,
  "suspected_loops": 0,
  "run_outcome": "PASS",
  "resilience_score": 94
}
```

**`run_outcome`** rules:
- `PASS` — no upstream failures and no suspected loops
- `DEGRADED` — some failures but at least one success (partial recovery)
- `FAIL` — all requests failed or loops detected with no successes

**`resilience_score`** formula (0–100):
```
100
  - (injected_faults    × 3)
  - (upstream_failures  × 12)
  - (duplicate_requests × 2)
  - (suspected_loops    × 10)
```

A score above 80 with `PASS` is a healthy result. A score below 60 or a `FAIL` outcome means your app is not handling failures gracefully.

**`duplicate_requests`**: the same request body (SHA-256 fingerprint) was seen more than once. This is normal for retry loops — it means the app is retrying.

**`suspected_loops`**: the same fingerprint was seen more than twice. This is a warning sign that the app may be stuck in an infinite retry loop rather than giving up or falling back.

Note: some agent frameworks legitimately issue multiple near-identical completions. Treat these counters as investigation signals, not definitive bugs.

## Common Patterns

### Local dev — fastest setup

```bash
agentbreak start --mode mock --scenario mixed-transient --fail-rate 0.2
export OPENAI_BASE_URL=http://localhost:5000/v1
export OPENAI_API_KEY=dummy
python my_app.py
```

### CI — deterministic run

```bash
agentbreak start --mode mock --scenario rate-limited --fail-rate 0.3 --seed 42 &
sleep 1
OPENAI_BASE_URL=http://localhost:5000/v1 OPENAI_API_KEY=dummy python my_app.py
curl http://localhost:5000/_agentbreak/scorecard
```

Using `--seed` makes every run inject faults in the same order, so CI failures are reproducible.

### Test specific error codes

```bash
# Only 401 and 403 — check auth error handling
agentbreak start --mode mock --error-codes 401,403 --fail-rate 0.5

# Exact split — 30% 500, 20% 429, 50% success
agentbreak start --mode mock --faults 500=0.3,429=0.2
```

### Proxy mode with real upstream

```bash
agentbreak start \
  --mode proxy \
  --upstream-url https://api.openai.com \
  --scenario provider-flaky \
  --fail-rate 0.25
export OPENAI_BASE_URL=http://localhost:5000/v1
export OPENAI_API_KEY=sk-...   # real key required in proxy mode
```

### Run the bundled example

```bash
agentbreak start --mode mock --scenario mixed-transient --fail-rate 0.3 &
cd examples/simple_langchain
pip install -r requirements.txt
OPENAI_API_KEY=dummy OPENAI_BASE_URL=http://localhost:5000/v1 python main.py
curl http://localhost:5000/_agentbreak/scorecard
```

## Debugging

**App not connecting:**
- Confirm `OPENAI_BASE_URL=http://localhost:5000/v1` (include `/v1`)
- Check the port with `curl http://localhost:5000/healthz`

**All requests failing (not just the expected fault rate):**
- In mock mode, set `OPENAI_API_KEY=dummy` — any non-empty string works
- In proxy mode, provide a real API key and verify `--upstream-url` has no trailing slash and no `/v1`

**Score is 0 / outcome is FAIL but fail-rate is low:**
- Check `/_agentbreak/requests` — if `upstream_failures` equals `requests_seen`, the upstream is unreachable, not AgentBreak injecting faults

**`suspected_loops` is high:**
- The app is re-sending the same message body repeatedly. Check retry logic — it should have a max retry count and exponential backoff, and should give up after N attempts rather than looping forever.

**`duplicate_requests` but not `suspected_loops`:**
- The app is retrying (seen twice) but not looping (not seen three or more times). This is expected healthy retry behavior.

## Gotchas

1. **`--latency-min` / `--latency-max` are in seconds**, not milliseconds. A value of `5` means a 5-second delay.
2. **In mock mode, `OPENAI_API_KEY` can be any non-empty string.** `dummy` works fine.
3. **In proxy mode, `OPENAI_API_KEY` must be a real key** or the upstream will reject the request.
4. **`--faults` total must be ≤ 1.0.** `500=0.6,429=0.5` will be rejected. The remainder of the probability is pass-through.
5. **`--faults` overrides `--scenario` for which codes get injected**, but `--scenario` still determines the scenario name shown in logs.
6. **Config file is loaded from `./config.yaml` automatically.** If the file exists and you want to ignore it, pass `--config /dev/null`.
7. **The mock response body is always `"AgentBreak mock response."`** — it does not stream and does not call tools. If your app requires tool calls or streaming, use proxy mode.
8. **`request_count` in `config.yaml` is read by the example scripts**, not by AgentBreak itself. The server runs until stopped.

## MCP Proxy

AgentBreak also proxies MCP (Model Context Protocol) servers using JSON-RPC 2.0. The MCP proxy runs on port 5001 by default.

```
mock mode:   MCP client → AgentBreak MCP proxy → stub response (or injected fault)
proxy mode:  MCP client → AgentBreak MCP proxy → real MCP server (or injected fault)
```

### MCP Modes

| Mode    | When to use                                              |
|---------|----------------------------------------------------------|
| `mock`  | Local dev, CI, no real MCP server needed                 |
| `proxy` | End-to-end testing with a real MCP server                |

### MCP Scenarios

| Scenario                    | Fail rate | Codes          | Latency | What it tests                        |
|-----------------------------|-----------|----------------|---------|--------------------------------------|
| `mcp-tool-failures`         | 30%       | 429, 500, 503  | none    | Tool call retry and backoff          |
| `mcp-resource-unavailable`  | 50%       | 404, 503       | none    | Resource read fallback handling      |
| `mcp-slow-tools`            | 0%        | none           | 90%     | Timeout handling for slow tools      |
| `mcp-initialization-failure`| 50%       | 500, 503       | none    | Initialization retry logic           |
| `mcp-mixed-transient`       | 20%       | 429, 500, 503  | 10%     | General resilience / brownout        |

### MCP CLI Reference

```
agentbreak mcp start [OPTIONS]

  --mode TEXT                   proxy | mock  (default: mock)
  --upstream-url TEXT           Base URL of the MCP server
  --upstream-transport TEXT     Transport: http | sse | stdio  (default: http)
  --upstream-command TEXT       Command for stdio transport
  --upstream-timeout FLOAT      Timeout in seconds (default: 30)
  --scenario TEXT               Built-in MCP scenario name
  --fail-rate FLOAT             Probability of injecting a fault (0.0–1.0)
  --fault-codes TEXT            Comma-separated codes: 429,500,503
  --latency-p FLOAT             Probability of injecting latency
  --latency-min FLOAT           Min delay in seconds (default: 5)
  --latency-max FLOAT           Max delay in seconds (default: 15)
  --seed INT                    Fix random seed for deterministic runs
  --port INT                    Port to bind on (default: 5001)
```

```
agentbreak mcp test [--url URL] [--transport http|stdio] [--command CMD]
agentbreak mcp list-tools [--url URL] [--transport http|stdio] [--command CMD]
agentbreak mcp call-tool TOOL [--args JSON] [--url URL] [--transport http|stdio]
```

### MCP Useful Endpoints

```bash
curl http://localhost:5001/_agentbreak/mcp/scorecard
curl http://localhost:5001/_agentbreak/mcp/tool-calls
curl http://localhost:5001/healthz
```

### MCP Scorecard

```json
{
  "requests_seen": 15,
  "injected_faults": 3,
  "latency_injections": 1,
  "upstream_successes": 12,
  "upstream_failures": 3,
  "duplicate_requests": 2,
  "suspected_loops": 0,
  "tool_calls": 8,
  "resource_reads": 3,
  "init_requests": 1,
  "method_counts": {"initialize": 1, "tools/call": 8, "tools/list": 3},
  "tool_successes_by_name": {"echo": 5, "get_time": 3},
  "tool_failures_by_name": {"echo": 1},
  "run_outcome": "DEGRADED",
  "resilience_score": 73
}
```

`run_outcome`: `PASS` (no failures, no loops), `DEGRADED` (some failures, some successes), `FAIL` (all failed or loops with no successes).

`resilience_score` formula: `100 - (injected_faults × 3) - (upstream_failures × 12) - (duplicate_requests × 2) - (suspected_loops × 10)`

### MCP Error Code Mapping

AgentBreak maps HTTP-style fault codes to MCP JSON-RPC 2.0 error codes:

| HTTP code | MCP error code | Meaning                  |
|-----------|----------------|--------------------------|
| 400, 413  | -32600         | Invalid request          |
| 401, 403  | -32603         | Auth/permission failure  |
| 404       | -32601         | Resource not found       |
| 429       | -32000         | Rate limit / tool error  |
| 500, 503  | -32603         | Internal error           |

### MCP Common Patterns

```bash
# Local dev — mock mode, no real server
agentbreak mcp start --mode mock --scenario mcp-mixed-transient --fail-rate 0.2

# CI — deterministic run
agentbreak mcp start --mode mock --scenario mcp-tool-failures --seed 42 &
python my_mcp_app.py
curl http://localhost:5001/_agentbreak/mcp/scorecard

# Proxy mode — real MCP server via HTTP
agentbreak mcp start --mode proxy --upstream-url http://localhost:8080 --fail-rate 0.3

# Proxy mode — real MCP server via stdio
agentbreak mcp start --mode proxy \
  --upstream-transport stdio \
  --upstream-command 'python my_server.py' \
  --fail-rate 0.2

# Test connectivity to any MCP server
agentbreak mcp test --url http://localhost:8080
agentbreak mcp list-tools --url http://localhost:8080
agentbreak mcp call-tool echo --args '{"text": "hello"}' --url http://localhost:8080
```

### MCP Debugging

**MCP client not connecting:**
- Confirm the client URL is `http://localhost:5001/mcp` (include `/mcp` path)
- Check with `curl http://localhost:5001/healthz`

**All MCP requests failing:**
- In mock mode, any requests should succeed (unless fail-rate is 1.0)
- In proxy mode, verify `--upstream-url` and that the real server is running
- Check `/_agentbreak/mcp/scorecard` — if `upstream_failures` equals `requests_seen`, the upstream is unreachable

**MCP errors always have HTTP 200:**
- This is correct. MCP uses JSON-RPC 2.0 where errors are in the response body, not the HTTP status.

**`suspected_loops` is high:**
- The same tool call (same name + arguments) was seen 3+ times. Check your retry logic has a max count.

### MCP Gotchas

1. **MCP proxy listens on port 5001**, not 5000. The OpenAI proxy uses 5000.
2. **Injected MCP errors always return HTTP 200** with a JSON-RPC error body — this is the MCP spec.
3. **Mock tool responses are always `"Mock result for tool: <name>"`** — they do not call real backends.
4. **`--upstream-command` for stdio** must be a shell command string, not a list. Quote complex commands.
5. **Fingerprinting excludes the JSON-RPC `id` field**, so retries with new IDs are still detected as duplicates.
