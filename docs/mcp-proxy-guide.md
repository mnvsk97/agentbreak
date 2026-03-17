# MCP Proxy Guide

AgentBreak's MCP proxy lets you test how your app behaves when an MCP server is slow, flaky, or
returning errors. It implements the [Model Context Protocol](https://modelcontextprotocol.io/)
(JSON-RPC 2.0) and supports stdio, SSE, and HTTP transports.

## Quick Start

Install AgentBreak:

```bash
pip install agentbreak
```

Start the MCP proxy in mock mode (no real MCP server needed):

```bash
agentbreak mcp start --mode mock --scenario mcp-mixed-transient --fail-rate 0.2
```

Point your MCP client at `http://localhost:5001/mcp`.

Check the scorecard:

```bash
curl http://localhost:5001/_agentbreak/mcp/scorecard
```

## Modes

| Mode    | What it does                                               |
|---------|------------------------------------------------------------|
| `mock`  | Returns stub responses — no real MCP server needed        |
| `proxy` | Forwards to a real MCP server and injects faults           |

### Mock mode

```bash
agentbreak mcp start --mode mock
agentbreak mcp start --mode mock --scenario mcp-tool-failures --fail-rate 0.3
```

Mock mode returns realistic stub responses for all standard MCP methods:
- `initialize` returns fake server capabilities
- `tools/list` returns two sample tools (`echo`, `get_time`)
- `tools/call` returns a mock text result
- `resources/list` returns two sample resource URIs
- `resources/read` returns sample file contents
- `prompts/list` returns a sample prompt template
- `prompts/get` returns a sample prompt message

### Proxy mode — HTTP upstream

```bash
agentbreak mcp start \
  --mode proxy \
  --upstream-url http://localhost:8080 \
  --scenario mcp-mixed-transient \
  --fail-rate 0.2
```

Requests are forwarded to `http://localhost:8080/mcp`.

### Proxy mode — SSE upstream

```bash
agentbreak mcp start \
  --mode proxy \
  --upstream-transport sse \
  --upstream-url http://localhost:8080 \
  --fail-rate 0.2
```

### Proxy mode — stdio upstream

```bash
agentbreak mcp start \
  --mode proxy \
  --upstream-transport stdio \
  --upstream-command 'python my_server.py' \
  --fail-rate 0.2
```

The command is launched as a subprocess. Requests are sent to its stdin and responses are read
from its stdout.

## Scenarios

Scenarios are named fault presets. Pass one with `--scenario`.

| Scenario                    | Fail rate | Codes injected   | Latency | What it tests                             |
|-----------------------------|-----------|------------------|---------|-------------------------------------------|
| `mcp-tool-failures`         | 30%       | 429, 500, 503    | none    | Tool call retry and backoff logic         |
| `mcp-resource-unavailable`  | 50%       | 404, 503         | none    | Resource read fallback handling           |
| `mcp-slow-tools`            | 0%        | none             | 90%     | Timeout handling for slow tool backends   |
| `mcp-initialization-failure`| 50%       | 500, 503         | none    | Initialization retry logic                |
| `mcp-mixed-transient`       | 20%       | 429, 500, 503    | 10%     | General resilience in brownout conditions |

Scenarios set default `--fail-rate` and latency values. CLI flags override these.

## CLI Reference

```
agentbreak mcp start [OPTIONS]

  --mode TEXT                   proxy | mock  (default: mock)
  --upstream-url TEXT           Base URL of the MCP server (proxy mode)
  --upstream-transport TEXT     Transport: http | sse | stdio  (default: http)
  --upstream-command TEXT       Command for stdio transport, e.g. "python server.py"
  --upstream-timeout FLOAT      Timeout in seconds for upstream requests (default: 30)
  --scenario TEXT               Built-in MCP scenario name (see table above)
  --fail-rate FLOAT             Probability of injecting a fault (0.0–1.0)
  --fault-codes TEXT            Comma-separated HTTP-style codes, e.g. 429,500,503
  --latency-p FLOAT             Probability of injecting latency on non-faulted requests
  --latency-min FLOAT           Min delay in seconds (default: 5)
  --latency-max FLOAT           Max delay in seconds (default: 15)
  --seed INT                    Fix random seed for deterministic runs
  --port INT                    Port to bind on (default: 5001)
```

```
agentbreak mcp test [OPTIONS]

  --url TEXT            URL of the AgentBreak MCP proxy or upstream (default: http://localhost:5001)
  --transport TEXT      Transport: http | stdio  (default: http)
  --command TEXT        Command for stdio transport
```

```
agentbreak mcp list-tools [OPTIONS]

  --url TEXT            URL of the MCP proxy or server (default: http://localhost:5001)
  --transport TEXT      Transport: http | stdio
  --command TEXT        Command for stdio transport
```

```
agentbreak mcp call-tool TOOL_NAME [OPTIONS]

  --args TEXT           JSON-encoded arguments dict, e.g. '{"text": "hello"}'
  --url TEXT            URL of the MCP proxy or server (default: http://localhost:5001)
  --transport TEXT      Transport: http | stdio
  --command TEXT        Command for stdio transport
```

## MCP Error Codes

AgentBreak maps HTTP-style fault codes to MCP JSON-RPC 2.0 error codes.

| HTTP code | MCP error code | Message                                           |
|-----------|----------------|---------------------------------------------------|
| 400       | -32600         | Invalid request injected by AgentBreak.           |
| 401       | -32603         | Authentication failure injected by AgentBreak.    |
| 403       | -32603         | Permission failure injected by AgentBreak.        |
| 404       | -32601         | Resource not found injected by AgentBreak.        |
| 413       | -32600         | Request too large injected by AgentBreak.         |
| 429       | -32000         | Rate limit exceeded by AgentBreak fault injection.|
| 500       | -32603         | Upstream failure injected by AgentBreak.          |
| 503       | -32603         | Service unavailable injected by AgentBreak.       |

Standard JSON-RPC 2.0 error codes:

| Code    | Name              | Meaning                                |
|---------|-------------------|----------------------------------------|
| -32700  | Parse error       | Invalid JSON received                  |
| -32600  | Invalid request   | JSON-RPC structure is invalid          |
| -32601  | Method not found  | Method or resource does not exist      |
| -32602  | Invalid params    | Invalid method parameters              |
| -32603  | Internal error    | Internal JSON-RPC error               |
| -32000  | Server error      | MCP tool error (reserved range)        |

## Useful Endpoints

```bash
# MCP resilience scorecard
curl http://localhost:5001/_agentbreak/mcp/scorecard

# Last 20 tool calls with fingerprints and bodies
curl http://localhost:5001/_agentbreak/mcp/tool-calls

# Health check
curl http://localhost:5001/healthz
```

Stop the server with `Ctrl+C` to print the final scorecard in the terminal.

## Scorecard Reference

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
  "method_counts": {
    "initialize": 1,
    "tools/list": 3,
    "tools/call": 8,
    "resources/list": 2,
    "resources/read": 3
  },
  "tool_successes_by_name": {"echo": 5, "get_time": 3},
  "tool_failures_by_name": {"echo": 1},
  "resource_reads_by_uri": {"file:///example/readme.txt": 2},
  "resource_failures_by_uri": {"file:///example/data.json": 1},
  "run_outcome": "DEGRADED",
  "resilience_score": 73
}
```

`run_outcome` values:
- `PASS` — no upstream failures and no suspected loops
- `DEGRADED` — some failures but at least one success
- `FAIL` — all requests failed or loops detected with no successes

`resilience_score` formula (0–100):

```
100
  - (injected_faults    × 3)
  - (upstream_failures  × 12)
  - (duplicate_requests × 2)
  - (suspected_loops    × 10)
```

A score above 80 with `PASS` is a healthy result.

`duplicate_requests`: the same tool call (SHA-256 fingerprint of method + tool name + arguments)
was seen more than once. Normal for retry loops — the app is retrying.

`suspected_loops`: the same fingerprint was seen more than twice. Warning sign that the app may
be stuck in an infinite retry loop.

## Duplicate Detection and Loop Tracking

AgentBreak fingerprints each MCP request using SHA-256:

- For `tools/call`: fingerprint covers `method + tool name + arguments` (not the request `id`)
- For all other methods: fingerprint covers `method + full params`

This means identical tool invocations with different JSON-RPC IDs still collide, so retries are
detected correctly even when the client generates a new `id` for each attempt.

## Configuration File

AgentBreak reads `config.yaml` from the current directory automatically.

```yaml
# MCP proxy configuration
mcp_mode: mock                              # disabled | mock | proxy
mcp_upstream_transport: http               # http | sse | stdio
mcp_upstream_url: http://localhost:8080
mcp_upstream_command: "python server.py"   # for stdio transport
mcp_fail_rate: 0.2
mcp_error_codes: [429, 500, 503]
latency_p: 0.1
latency_min: 5
latency_max: 15
```

CLI flags override config file values.

## Examples

See [examples/mcp_client/](../examples/mcp_client/) for:
- `main.py` — basic MCP client demonstrating tool calls and resource reads through the proxy
- `retry_example.py` — retry logic with exponential backoff on MCP errors

Run the examples:

```bash
# Start the proxy in mock mode
agentbreak mcp start --mode mock &

# Run the basic example
cd examples/mcp_client
pip install -r requirements.txt
python main.py

# Run the retry example with 30% fault rate
agentbreak mcp start --mode mock --fail-rate 0.3 &
python retry_example.py
```

## FAQ

**Q: Why does AgentBreak always return HTTP 200 even for injected faults?**

MCP uses JSON-RPC 2.0 over HTTP. Errors are represented in the JSON body (`"error": {...}`),
not in the HTTP status code. A status 200 with an error body is correct MCP behavior.

**Q: My MCP client doesn't see injected faults — it always succeeds.**

Check that your client is pointed at the AgentBreak proxy URL (`http://localhost:5001/mcp`) and
not directly at the upstream server. Verify with `curl http://localhost:5001/healthz`.

**Q: Can I use AgentBreak's MCP proxy with Claude Code?**

Yes. Set your MCP server URL to `http://localhost:5001` in your Claude Code MCP configuration.
AgentBreak will intercept all tool and resource calls made by Claude Code.

**Q: What is the difference between `--fail-rate` and `--fault-codes`?**

`--fail-rate` controls how often a fault fires (probability, 0.0–1.0).
`--fault-codes` controls which HTTP-style error codes are used when a fault fires (comma-separated).
Both can be combined: `--fail-rate 0.3 --fault-codes 429,500`.

**Q: How does stdio transport work?**

AgentBreak launches the command as a subprocess, writes JSON-RPC requests to its stdin (one per
line), and reads JSON-RPC responses from its stdout. The subprocess must implement the MCP
stdio protocol.

**Q: Can I run both the OpenAI proxy and the MCP proxy at the same time?**

Yes. The OpenAI proxy runs on port 5000 (`agentbreak start`) and the MCP proxy runs on port 5001
(`agentbreak mcp start`). They are independent FastAPI apps.

**Q: Why is `suspected_loops` high even though my app has a retry limit?**

The threshold for `suspected_loops` is 3+ identical requests (same fingerprint). If your retry
limit is 3 or more, the counter will increment. Consider lowering your retry limit or increasing
jitter so each retry looks different enough to not loop-detect.

**Q: Can I use a fixed random seed for CI?**

Yes. Pass `--seed INT` to make fault injection deterministic:

```bash
agentbreak mcp start --mode mock --scenario mcp-tool-failures --seed 42
```

Every run with the same seed injects faults in the same order, making CI failures reproducible.

**Q: How do I test a specific MCP server without running my full app?**

Use the built-in test and tool commands:

```bash
agentbreak mcp test --url http://localhost:8080
agentbreak mcp list-tools --url http://localhost:8080
agentbreak mcp call-tool echo --args '{"text": "hello"}' --url http://localhost:8080
```

These commands connect directly to the server (bypassing the proxy) and print the results.
