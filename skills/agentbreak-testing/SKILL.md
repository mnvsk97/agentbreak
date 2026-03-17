---
name: agentbreak-testing
description: Use when testing an LLM app or agent with AgentBreak. Starts AgentBreak in mock or proxy mode, chooses a scenario or weighted faults, points the target app at OPENAI_BASE_URL, runs the target command, and checks the scorecard endpoints. Full reference: .claude/commands/agentbreak.md
---

# AgentBreak Testing

Use this skill when the user wants to run chaos tests against an OpenAI-compatible app with AgentBreak.

## Workflow

1. Decide mode:
   - `mock` for zero-upstream local testing
   - `proxy` for fault injection in front of a real upstream
2. Prefer scenarios first:
   - `mixed-transient`
   - `rate-limited`
   - `provider-flaky`
   - `non-retryable`
   - `brownout`
3. Use weighted faults only when the user asks for exact percentages such as `500=0.3,429=0.2`.
4. Install AgentBreak from the repo root if it is not already installed:

```bash
pip install -e .
```

5. Start AgentBreak from the repo root:

```bash
agentbreak start --mode mock --scenario mixed-transient --fail-rate 0.2 --port 5000
```

Or:

```bash
agentbreak start --mode proxy --upstream-url https://api.openai.com --scenario mixed-transient --fail-rate 0.2 --port 5000
```

6. Point the target app at AgentBreak:

```bash
export OPENAI_BASE_URL=http://127.0.0.1:5000/v1
export OPENAI_API_KEY=dummy
```

Use a real API key only when proxying to a real upstream.

7. Run the target command or one of the examples:

```bash
OPENAI_API_KEY=dummy OPENAI_BASE_URL=http://127.0.0.1:5000/v1 python examples/simple_langchain/main.py
```

8. Inspect the result:

```bash
curl http://127.0.0.1:5000/_agentbreak/scorecard
curl http://127.0.0.1:5000/_agentbreak/requests
```

9. Summarize:
   - requests seen
   - injected faults
   - duplicate requests
   - suspected loops
   - run outcome
   - resilience score

When reporting duplicate requests or suspected loops, note that some agent frameworks legitimately issue repeated underlying completions. Treat those counters as investigation signals, not automatic proof of a bug.

## Install

Keep this skill as a normal Agent Skills folder:

```text
skills/
  agentbreak-testing/
    SKILL.md
```

If your agent runner has a separate skills directory, copy the whole `agentbreak-testing` folder there rather than just the markdown file.

## Invoke

Ask for the skill by name, for example:

- `Use the agentbreak-testing skill to run the simple_langchain example in mock mode.`
- `Use the agentbreak-testing skill to run proxy mode against https://api.openai.com and report the scorecard.`
- `Use the agentbreak-testing skill to run the simple_langchain example with AGENTBREAK_REQUEST_COUNT=10.`

## MCP Proxy Testing

Use this section when the user wants to test an MCP (Model Context Protocol) server or an app that uses MCP tools and resources.

### MCP Workflow

1. Decide mode:
   - `mock` for zero-upstream local testing (no real MCP server needed)
   - `proxy` for fault injection in front of a real MCP server

2. Prefer MCP scenarios first:
   - `mcp-tool-failures` — 30% fail rate with 429/500/503
   - `mcp-resource-unavailable` — 50% fail with 404/503
   - `mcp-slow-tools` — 90% latency injection (5–15s)
   - `mcp-initialization-failure` — 50% fail on init
   - `mcp-mixed-transient` — 20% fail + 10% latency

3. Start the MCP proxy on port 5001:

```bash
agentbreak mcp start --mode mock --scenario mcp-mixed-transient --fail-rate 0.2
```

Or for proxy mode with a real HTTP upstream:

```bash
agentbreak mcp start --mode proxy --upstream-url http://localhost:8080 --fail-rate 0.2
```

Or for proxy mode with a stdio upstream:

```bash
agentbreak mcp start --mode proxy \
  --upstream-transport stdio \
  --upstream-command 'python my_server.py' \
  --fail-rate 0.2
```

4. Point the MCP client at `http://localhost:5001/mcp`.

5. Run the target application.

6. Inspect the MCP scorecard:

```bash
curl http://localhost:5001/_agentbreak/mcp/scorecard
curl http://localhost:5001/_agentbreak/mcp/tool-calls
```

7. Summarize:
   - requests seen, tool calls, resource reads, init requests
   - injected faults and latency injections
   - duplicate requests and suspected loops
   - run outcome and resilience score
   - per-tool and per-URI success/failure counts

8. Test individual MCP tools directly:

```bash
agentbreak mcp test --url http://localhost:5001
agentbreak mcp list-tools --url http://localhost:5001
agentbreak mcp call-tool echo --args '{"text": "hello"}' --url http://localhost:5001
```

### MCP Notes

- The MCP proxy always returns HTTP 200 — MCP errors are in the JSON-RPC body, not the status code.
- `duplicate_requests` means the same tool call (name + arguments) was seen more than once — normal for retries.
- `suspected_loops` means the same tool call was seen 3+ times — check max retry count.
- For CI, use `--seed INT` to make fault injection deterministic and reproducible.
- The OpenAI proxy uses port 5000; the MCP proxy uses port 5001. Both can run simultaneously.
- Full MCP reference: see `docs/mcp-proxy-guide.md` in the AgentBreak repo.

## Notes

- If `config.yaml` exists, `agentbreak start` will load it automatically.
- CLI flags override `config.yaml`.
- The examples also read `request_count` from `config.yaml`, or `AGENTBREAK_REQUEST_COUNT` if it is set.
- For first-time users, prefer `mock` mode because it avoids upstream setup.
- For end-to-end resilience testing, prefer `proxy` mode.
