---
name: agentbreak
description: >
  Chaos-test any LLM agent using AgentBreak. Uses the AgentBreak MCP tools to analyze the codebase,
  generate chaos scenarios, start the proxy, wire the agent, and interpret results.
  Use when the user wants to test agent resilience or run AgentBreak.
---

# AgentBreak — Chaos Test Your Agent

This skill orchestrates the AgentBreak MCP tools to chaos-test an agent end-to-end.

## Prerequisites

The AgentBreak MCP server must be configured in the user's Claude Code settings:

```json
{
  "mcpServers": {
    "agentbreak": {
      "command": "agentbreak",
      "args": ["mcp-server"]
    }
  }
}
```

If not configured, help the user add it, then proceed.

If `agentbreak` CLI is not installed, run:
```bash
pip install agentbreak[plugin]
```

## Workflow

Use the AgentBreak MCP tools in this order. **Ask the user to confirm before each major step.**

### Step 1: Initialize

Call `agentbreak_init` to create `.agentbreak/` config if it doesn't exist.

### Step 2: Analyze

Call `agentbreak_analyze` to scan the codebase. Present findings to the user:

> "Here's what I found:
> - **Provider:** [openai/anthropic]
> - **Framework:** [langgraph/langchain/etc.]
> - **MCP tools:** [detected/none]
> - **Error handling:** [has retry logic / no retry logic]
>
> Does this look correct?"

If the provider is ambiguous or wrong, ask the user which one to use.

### Step 3: Generate Config

Call `agentbreak_generate_config` with the analysis findings. Present the generated scenarios:

> "Here are the chaos scenarios I generated:
> | Scenario | Target | Fault |
> |----------|--------|-------|
> | ... | ... | ... |
>
> Want to adjust anything?"

### Step 4: Start Proxy

1. Call `agentbreak_validate` to check config.
2. Call `agentbreak_start` to start the proxy.

### Step 5: Wire Agent & Run

1. Call `agentbreak_wire` with the detected provider and port.
2. Tell the user their agent is now wired to AgentBreak.
3. Start the agent (look for its normal run command in the codebase).
4. Run 3-5 invocations with different prompts.
5. Call `agentbreak_scorecard` to verify traffic flowed (`requests_seen > 0`).

If `requests_seen` is 0, debug: the agent may not be reading the `.env` change (restart needed).

### Step 6: Results

1. Call `agentbreak_scorecard` to get the full results.
2. Call `agentbreak_stop` — this stops the proxy **and auto-reverts the .env**.
3. Produce the Chaos Test Report:

> ## Chaos Test Report
>
> **Score:** [score]/100 — [PASS/DEGRADED/FAIL]
>
> ### What Happened
> - **[scenario]:** [Did the agent retry, crash, loop, or succeed?]
>
> ### Issues Found
> | # | Issue | Severity | Evidence |
> |---|-------|----------|----------|
>
> ### Fixes
> For each issue, give a specific code fix referencing actual files from the codebase.
>
> ### Next Steps
> - Issues found → "Want me to apply these fixes?"
> - Score 80+ → "Your agent is resilient. Consider adding chaos tests to CI."

## Safety

- `agentbreak_stop` **automatically reverts** the .env if still wired — the user's config is never left broken.
- `agentbreak_revert` can be called at any time to restore the original .env.
- `agentbreak_status` shows current state (proxy running, env wired).

## Rules

- **Determine one provider** before generating config. Never test both at once.
- **Always confirm** findings and scenarios with the user before proceeding.
- **If you can't start the agent programmatically**, ask the user to trigger it manually.
- **If scorecard shows `requests_seen: 0`**, the agent isn't wired correctly — debug before continuing.
- **Always call `agentbreak_stop`** when done. Never leave the proxy running or .env modified.
