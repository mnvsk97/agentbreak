# MCP Client Example

Two scripts that show how to talk to an MCP server (or the AgentBreak MCP
proxy) using plain `httpx` and JSON-RPC 2.0 — no MCP SDK required.

## Scripts

| Script | What it shows |
|--------|--------------|
| `main.py` | Initialize, list tools, call tools, list and read resources |
| `retry_example.py` | Retry transient MCP errors with exponential back-off |

## Setup

```bash
cd examples/mcp_client
pip install -r requirements.txt
```

## Quick start — mock mode (no real MCP server needed)

In one terminal, start the AgentBreak MCP proxy in mock mode:

```bash
python -m agentbreak.mcp_proxy --mode mock --fail-rate 0
```

In another terminal, run the basic example:

```bash
python main.py
```

Expected output:

```
Connecting to MCP proxy at http://localhost:5001/mcp
Connected to server: agentbreak-mock v1.0.0

Available tools (2):
  echo: Echo back the input text.
  get_time: Return the current UTC time.

Calling tool: echo
  Result: Mock result for tool: echo

Calling tool: get_time
  Result: Mock result for tool: get_time

Available resources (2):
  file:///example/readme.txt: README
  file:///example/data.json: Data

Reading resource: file:///example/readme.txt
  Content (text/plain): Mock content for resource: file:///example/readme.txt

Scorecard: PASS (score 100/100)
  Requests: 6, Faults injected: 0
```

## Retry example — with fault injection

Start the proxy with 30 % fault rate:

```bash
python -m agentbreak.mcp_proxy --mode mock --fail-rate 0.3 --seed 42
```

Run the retry example:

```bash
python retry_example.py
```

The script retries transient errors (rate limits, server errors) with
exponential back-off and gives up on permanent errors (invalid request,
method not found).

## Proxy mode — real MCP server

Point the proxy at a real MCP server over HTTP:

```bash
python -m agentbreak.mcp_proxy \
  --mode proxy \
  --upstream-transport http \
  --upstream-url http://localhost:8080 \
  --fail-rate 0.1
```

Or over stdio (e.g. a filesystem MCP server):

```bash
python -m agentbreak.mcp_proxy \
  --mode proxy \
  --upstream-transport stdio \
  --upstream-command "npx -y @modelcontextprotocol/server-filesystem /tmp" \
  --fail-rate 0.1
```

Then run either example script — the `MCP_PROXY_URL` environment variable
controls which proxy the client connects to (defaults to
`http://localhost:5001/mcp`):

```bash
MCP_PROXY_URL=http://localhost:5001/mcp python main.py
```

## MCP error codes reference

| Code | Meaning | Retryable? |
|------|---------|-----------|
| -32700 | Parse error | No |
| -32600 | Invalid request | No |
| -32601 | Method not found | No |
| -32602 | Invalid params | No |
| -32603 | Internal error | Yes |
| -32000 | Tool error / rate limit | Yes |
