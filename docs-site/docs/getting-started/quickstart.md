# Quickstart

Get AgentBreak running in under a minute.

## 1. Install

```bash
pip install agentbreak
```

## 2. Initialize

```bash
agentbreak init
```

This creates `.agentbreak/` with two config files:

- **`application.yaml`** — what to proxy (LLM/MCP mode, upstream URLs, port)
- **`scenarios.yaml`** — what faults to inject (includes a standard preset with baseline scenarios)

## 3. Start the proxy

```bash
agentbreak serve
```

AgentBreak starts on `http://localhost:5005`.

## 4. Point your agent at it

=== "OpenAI"

    ```bash
    export OPENAI_BASE_URL=http://localhost:5005/v1
    ```

=== "Anthropic"

    ```bash
    export ANTHROPIC_BASE_URL=http://localhost:5005
    ```

Your agent code doesn't change — just the base URL.

## 5. Run your agent

Run your agent as you normally would. AgentBreak intercepts traffic and injects faults based on your scenarios.

## 6. Check results

```bash
curl localhost:5005/_agentbreak/scorecard
```

You'll get a JSON response with:

- **`resilience_score`** — 0 to 100
- **`run_outcome`** — `PASS`, `DEGRADED`, or `FAIL`
- **`injected_faults`** — how many faults were applied
- **`suspected_loops`** — whether your agent got stuck

## Mock vs proxy mode

By default, AgentBreak runs in **mock mode** — no API keys needed, it returns synthetic responses. Both LLM and MCP support mock mode.

To test against real APIs, switch to **proxy mode**:

```yaml
# .agentbreak/application.yaml
llm:
  enabled: true
  mode: proxy
  upstream_url: https://api.openai.com    # or https://api.anthropic.com
  auth:
    type: bearer
    env: OPENAI_API_KEY                   # or ANTHROPIC_API_KEY

mcp:
  enabled: true
  mode: proxy
  upstream_url: http://localhost:8001/mcp
```

Verify your credentials before running tests:

```bash
agentbreak validate --test-connection
```

## Next steps

- [How it works](how-it-works.md) — understand the proxy model
- [Scenarios reference](../reference/scenarios.md) — customize your faults
- [Testing methodology](../guides/testing-methodology.md) — design effective tests
