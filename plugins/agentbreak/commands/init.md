---
description: Initialize AgentBreak — set up chaos testing, fault injection, and resilience testing for your LLM agent
allowed-tools: Read, Glob, Grep, Bash, Edit, Write, AskUserQuestion
---

# AgentBreak -- Init

You are helping the user set up AgentBreak for chaos testing their agent.

## Your job

1. Check AgentBreak is installed
2. Run `agentbreak init`
3. Analyze the codebase
4. Ask: mock or proxy mode?
5. Configure `application.yaml` and `scenarios.yaml` based on findings + mode
6. Validate the config (+ test connection if proxy)
7. If MCP enabled, run `agentbreak inspect`
8. Offer project-specific scenarios

Ask the user to confirm before writing config.

## Step 1: Install & update check

First detect the user's Python environment and install accordingly:

```bash
# Detect environment
which uv 2>/dev/null && echo "HAS_UV=1" || echo "HAS_UV=0"
python3 -c "import sys; print('IN_VENV=1' if sys.prefix != sys.base_prefix else 'IN_VENV=0')" 2>/dev/null
```

Based on the result:
- **uv available** → `uv pip install agentbreak`
- **In a venv** → `pip install agentbreak`
- **Neither (bare system Python)** → suggest `python3 -m venv .venv && source .venv/bin/activate && pip install agentbreak`, or `uv pip install agentbreak` if they have uv

Then check it works:

```bash
agentbreak --help
```

After confirming it's installed, check for updates:

```bash
pip index versions agentbreak 2>/dev/null | head -1
agentbreak --version
```

Compare the installed version with the latest on PyPI. If a newer version is available, tell the user:

> "AgentBreak **X.Y.Z** is installed, but **A.B.C** is available. Run `pip install --upgrade agentbreak` to update."

If `pip index` is not available (older pip), use this fallback:

```bash
pip install agentbreak --dry-run 2>&1 | grep -i "already satisfied\|would install"
```

Don't block on this — if the check fails, just skip it and continue.

## Step 2: Init

```bash
agentbreak init
```

Creates `.agentbreak/` with default `application.yaml` and `scenarios.yaml`.

## Step 3: Analyze the codebase

Scan the project to understand the agent. Look for:

- **Provider:** Search for `openai`, `anthropic`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` in code and `.env`
- **Framework:** Search for `langgraph`, `langchain`, `crewai`, `autogen`, `openai` SDK usage
- **MCP tools:** Search for `mcp`, `MCPClient`, `tool_call` patterns
- **Error handling:** Search for `max_retries`, `retry`, `except`, `timeout`, `backoff`

Present findings:

> "Here's what I found:
> - **Provider:** [openai/anthropic]
> - **Framework:** [langgraph/langchain/openai SDK/etc.]
> - **MCP tools:** [detected/none]
> - **Error handling:** [has retry logic / no retry logic]
>
> Does this look correct?"

If the provider is ambiguous, ask which one to use.

## Step 4: Ask mode preference

After presenting codebase findings, ask the user:

> "How do you want to run chaos tests?"
>
> 1. **Mock mode** — No API keys needed. AgentBreak generates synthetic responses. Good for demos, CI, and testing fault handling logic.
> 2. **Proxy mode** — Real API traffic. AgentBreak sits between your agent and the real upstream, injecting faults into live calls. Requires valid API keys.

## Step 5: Configure

Based on analysis + mode choice, write `.agentbreak/application.yaml`:

**Mock mode:**

```yaml
llm:
  enabled: true
  mode: mock
mcp:
  enabled: true   # if MCP detected
  mode: mock
serve:
  port: 5005
```

**Proxy mode:**

```yaml
llm:
  enabled: true
  mode: proxy
  upstream_url: https://api.openai.com  # or anthropic URL
  auth:
    type: bearer
    env: OPENAI_API_KEY
mcp:
  enabled: true   # if MCP detected
  mode: proxy
  upstream_url: http://localhost:8001/mcp
  # auth: ...
serve:
  port: 5005
```

For proxy mode, use the detected upstream URLs and auth env vars from Step 3. If MCP was detected but no upstream URL was found, ask the user for it.

`agentbreak init` generates `scenarios.yaml` with a standard preset based on what's enabled:
- LLM only → `preset: standard` (6 baseline LLM scenarios)
- MCP only → `preset: standard-mcp` (7 baseline MCP scenarios)
- Both → `preset: standard-all` (13 baseline scenarios)

Present the generated config and ask for confirmation before writing.

## Step 6: Validate

```bash
agentbreak validate
```

If validation fails, fix the config and re-validate.

**If proxy mode is configured**, run an auth pre-check:

```bash
agentbreak validate --test-connection
```

This tests connectivity and auth against the upstream(s). Possible results:
- **OK** — upstream reachable, auth works. Proceed.
- **AUTH FAILED (401)** — bad API key or token. Help the user fix it before continuing.
- **FORBIDDEN (403)** — key valid but insufficient permissions.
- **CONNECTION FAILED** — wrong URL or upstream is down.
- **TIMEOUT** — upstream too slow to respond.

If auth fails, help the user fix the config (check env var name, verify the key is set, confirm URL). Re-run `--test-connection` until it passes. Do NOT proceed to chaos testing with broken auth — every test will fail for the wrong reason.

Skip `--test-connection` for mock mode (no upstream to check).

## Step 7: Inspect MCP (if enabled)

If `mcp.enabled: true` in `application.yaml`, discover the upstream tools:

```bash
agentbreak inspect
```

Expected output:
```
Discovered N MCP tools
Wrote registry: .agentbreak/registry.json
```

If this fails (e.g. 401 auth error, connection refused), **do NOT silently skip it**. Stop and ask the user:

> "MCP inspect failed: [error details]. Would you like to:
> 1. **Fix it** — check the token/URL and retry
> 2. **Skip MCP** — disable MCP testing and continue with LLM-only scenarios"

Wait for the user's answer before proceeding. Only disable MCP if they explicitly choose option 2.

In mock mode, inspect is not needed — skip this step.

## Step 8: Offer project-specific scenarios

After validation passes, tell the user what standard scenarios are included, then ask:

> "Standard chaos tests are ready — these cover baseline faults like rate limits, server errors, latency, bad JSON, empty responses, and schema violations.
>
> Want me to also analyze your codebase and generate project-specific scenarios? These target your specific tools, models, and failure modes."

- If **yes** → analyze the codebase (read MCP registry for tool names, scan code for specific models and integrations), generate targeted scenarios, append them under the `scenarios:` key in `scenarios.yaml` (keeping the preset), re-validate.
- If **no** → done, show next steps.

## Done

Tell the user:

> "AgentBreak is initialized. Run `/agentbreak:run-tests` to start chaos testing."

## Rules

- **Detect one provider.** Never configure both. If ambiguous, ask.
- **Always confirm** before writing config files.
- **Always validate** after writing config.
- **Port 5005** is the default (macOS AirPlay uses 5000).
