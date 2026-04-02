---
name: agentbreak
description: >
  Chaos-test any LLM agent using AgentBreak. Analyzes the codebase to detect framework, LLM provider,
  and MCP tools, generates tailored fault scenarios, starts a chaos proxy, guides the user through
  testing, and interprets results. Use when the user wants to test agent resilience, generate chaos
  scenarios, or run AgentBreak.
---

# AgentBreak — Chaos Test Your Agent

This skill runs the full AgentBreak workflow: analyze the codebase, generate chaos config, start the proxy, guide the user through testing, and interpret the scorecard.

## Workflow

Execute the steps in order. **Do not start the next step until the current step's checkpoint is complete and the user has confirmed.**

**Before starting each step**, tell the user what is about to happen:

> "I'm about to start **Step N: [Name]**. This will [brief description]. Here's what to expect: [what the user will need to review or answer]."

### Step 1: Setup

**What it does:** Installs AgentBreak and initializes the `.agentbreak/` config directory.

**Execute:**

1. Check if `agentbreak` CLI is available:
   ```bash
   which agentbreak || pip install agentbreak
   ```
2. If `.agentbreak/` does not exist, run:
   ```bash
   agentbreak init
   ```

No checkpoint needed — proceed to Step 2.

### Step 2: Analyze Codebase

**What it does:** Scans the user's codebase to detect their agent framework, LLM provider, MCP tools, and error handling patterns. This drives the config generation.

**Execute:** Use subagents to search in parallel for:

**LLM provider** (you MUST determine exactly one):
- OpenAI: `from openai`, `ChatOpenAI`, `langchain_openai`, `api.openai.com`, `OPENAI_API_KEY`, `model="gpt-*"`
- Anthropic: `from anthropic`, `ChatAnthropic`, `langchain_anthropic`, `api.anthropic.com`, `ANTHROPIC_API_KEY`, `model="claude-*"`

**Agent framework:** `langgraph`, `langchain`, `crewai`, `autogen`, `llama_index`, `smolagents`, or raw SDK usage

**MCP tool usage:** `MCPClient`, `tools/call`, `@mcp.tool`, `@tool` decorators, MCP server URLs

**API key env vars:** `os.getenv("*_API_KEY")`, `.env` files

**Error handling:** `try`/`except` around LLM calls, `retry`, `tenacity`, `backoff` imports, `max_retries`, `timeout=`

**Review checkpoint:**
Present findings to the user:

> "Here's what I found in your codebase:
>
> - **LLM Provider:** [OpenAI / Anthropic]
> - **Framework:** [LangGraph / OpenAI SDK / etc.]
> - **MCP tools:** [list tool names, or "none detected"]
> - **Error handling:** [has retry logic / no retry logic found]
>
> **Why this matters:** The provider determines which endpoint AgentBreak proxies (`/v1/chat/completions` for OpenAI, `/v1/messages` for Anthropic). The error handling patterns determine which fault scenarios are most valuable — if your agent has no retry logic, rate limit errors (429) will be especially revealing."

**Then use `AskUserQuestion`** with options like: "Looks correct, proceed", "Wrong provider — I use [other]", "I want to add/change something".

If the provider is ambiguous (both found, or neither), **ask the user directly** which provider to test.

### Step 3: Generate Config

**What it does:** Creates tailored `.agentbreak/application.yaml` and `.agentbreak/scenarios.yaml` based on the scan findings.

**Execute:**

**application.yaml:**
- `llm.mode`: `mock` (default — no API key needed for chaos testing) or `proxy` if user wants to test against real provider
- `mcp.enabled`: `true` if MCP tools were detected, with `upstream_url` from the codebase
- `serve.port`: 5005

**scenarios.yaml** — generate scenarios based on findings:
- **No retry logic found** → prioritize `http_error` scenarios (429, 500). The agent likely crashes on these.
- **No timeout handling** → prioritize `latency` scenarios with high delays.
- **MCP tools found** → add per-tool fault scenarios using `match.tool_name` for each tool.
- **Specific model found** → use `match.model` to target it.
- Always include at least: one error scenario, one latency scenario, one response mutation.
- Use `probability: 0.2-0.3` for realistic testing.

Write both files to `.agentbreak/`.

**Review checkpoint:**
Present the generated scenarios:

> "Here are the chaos scenarios I generated:
>
> | Scenario | Target | Fault | Probability |
> |----------|--------|-------|-------------|
> | [name] | [llm_chat/mcp_tool] | [kind] | [prob] |
> | ... | ... | ... | ... |
>
> **What each tests:**
> - [scenario name]: [one-line explanation of what it catches]
> - ...
>
> **What to check:** Are there specific failure modes you've seen in production that aren't covered? Any tools that should be excluded from fault injection?"

**Then use `AskUserQuestion`** with options like: "Looks good, proceed", "Add more scenarios", "Remove a scenario", "Change probabilities".

### Step 4: Start the Proxy

**What it does:** Runs MCP inspect (if needed), validates config, and starts the AgentBreak chaos proxy.

**Execute:**

1. If MCP is enabled and the upstream MCP server is running:
   ```bash
   agentbreak inspect
   ```
   If inspect fails, tell the user to start their MCP server first.

2. Validate:
   ```bash
   agentbreak validate
   ```
   Fix any errors before proceeding.

3. Check if history is enabled in `.agentbreak/application.yaml`. If not, ask the user if they want to enable it for run comparison. If yes, add `history: {enabled: true}` to the config.

4. Start the proxy. If the user provided context about what changed, pass it as a label:
   ```bash
   agentbreak serve -v --label "description of what changed" &
   ```
   If no label context was given:
   ```bash
   agentbreak serve -v &
   ```
   Wait for the health check to confirm it's running:
   ```bash
   curl -s http://localhost:{port}/healthz
   ```

**Review checkpoint:**

> "AgentBreak proxy is running on port {port}. Next I'll wire your agent to send traffic through it."

No `AskUserQuestion` needed here — proceed directly to Step 5.

### Step 5: Wire the Agent & Send Traffic

**What it does:** Connects the user's agent to AgentBreak, triggers a run, and waits for traffic to flow through the proxy.

**Execute:**

#### 5a. Find the LLM connection config

From the Step 2 scan, you already know how the agent connects to its LLM. Look for:
- **`.env` file**: env vars like `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, or custom vars like `TFY_GATEWAY_URL`, `LLM_BASE_URL`, etc.
- **Hardcoded in code**: `base_url=` in SDK constructors, `ChatOpenAI(base_url=...)`, `Anthropic(base_url=...)`, etc.

#### 5b. Rewire the agent to AgentBreak

**Back up and modify the `.env` file** (or equivalent config) to point at AgentBreak:

```bash
# Back up original
cp .env .env.backup
```

Then edit the `.env` to replace the LLM URL with the AgentBreak proxy:

**If OpenAI / OpenAI-compatible:**
- Change the base URL env var to `http://127.0.0.1:{port}/v1`
- If mock mode: set the API key to `dummy` (or leave the real key — mock mode ignores it)

**If Anthropic:**
- Change the base URL env var to `http://127.0.0.1:{port}`
- If mock mode: set the API key to `dummy`

**If MCP is also enabled:**
- Change the MCP URL env var to `http://127.0.0.1:{port}/mcp`

**IMPORTANT:** Some frameworks (`langgraph dev`, `dotenv`, subprocess launchers) ignore inline env var overrides and only read `.env` files. Always edit the actual `.env` file rather than relying on `export` or inline vars.

#### 5c. Start the agent

Start the agent using its normal run command. Common patterns:

```bash
# LangGraph
langgraph dev --port 8888 --no-browser

# Direct Python
python agent.py

# Other frameworks
python -m my_agent
```

Run this in the background and wait for it to be ready.

#### 5d. Trigger a run

Send a real request through the agent so LLM/MCP traffic flows through AgentBreak. Choose based on the agent type:

**If the agent has an HTTP API** (LangGraph, FastAPI, etc.):
```bash
# LangGraph example
THREAD=$(curl -s -X POST http://127.0.0.1:8888/threads -H "Content-Type: application/json" -d '{}')
THREAD_ID=$(echo "$THREAD" | python3 -c "import sys,json; print(json.load(sys.stdin)['thread_id'])")
curl -s -X POST "http://127.0.0.1:8888/threads/$THREAD_ID/runs/wait" \
  -H "Content-Type: application/json" \
  -d '{"assistant_id": "agent", "input": {"messages": [{"role": "user", "content": "your prompt here"}]}}'
```

**If the agent is a CLI script**: just run it.

**If you can't trigger the agent programmatically**: tell the user to trigger it manually and use `AskUserQuestion` to wait.

Run **3-5 invocations** to get enough data for a meaningful scorecard. Use different prompts to avoid loop detection.

#### 5e. Verify traffic flowed through AgentBreak

```bash
curl -s http://localhost:{port}/_agentbreak/scorecard
```

Check that `requests_seen > 0`. If it's 0, the agent isn't routing through AgentBreak — debug the connection:
- Check the agent logs for the URL it's hitting
- Verify the `.env` edit took effect (agent may need restart)
- Make sure the agent isn't caching a stale LLM client

#### 5f. Restore the original config

```bash
cp .env.backup .env && rm .env.backup
```

Stop the agent process.

**Review checkpoint:**

> "I ran {N} requests through your agent via AgentBreak. Here's what I saw in the proxy logs:
> [summary of faults that fired — e.g., "2 rate limits, 1 empty response, 1 latency spike"]
>
> Ready to see the full scorecard?"

**Then use `AskUserQuestion`**: "Show me the results" / "Run more traffic first"

### Step 6: Results & Action Plan

**What it does:** Reads the scorecard, analyzes what failed and why, and produces a structured report with concrete fixes. The report should be actionable — either the user can follow it, or Claude Code can continue working on the fixes directly.

**Execute:**

1. Fetch all data:
   ```bash
   curl -s http://localhost:{port}/_agentbreak/scorecard
   curl -s http://localhost:{port}/_agentbreak/requests
   # If MCP enabled:
   curl -s http://localhost:{port}/_agentbreak/mcp-scorecard
   curl -s http://localhost:{port}/_agentbreak/mcp-requests
   ```

2. Stop the proxy:
   ```bash
   kill %1
   ```

3. If history is enabled, compare with the most recent previous run:
   ```bash
   agentbreak history
   agentbreak history compare {previous_id} {current_id}
   ```

**Now produce the Chaos Test Report.** This is the most important output of the entire skill. Follow this structure exactly:

---

> ## Chaos Test Report
>
> **Agent:** [agent name/path]
> **Score:** [score]/100 — [PASS/DEGRADED/FAIL]
> **Date:** [timestamp]
>
> ### Traffic Summary
>
> | Metric | Value |
> |--------|-------|
> | Requests proxied | [N] |
> | Faults injected | [N] ([percentage]%) |
> | Latency injections | [N] |
> | Response mutations | [N] |
> | Upstream successes | [N] |
> | Upstream failures | [N] |
> | Duplicate requests | [N] |
> | Suspected loops | [N] |
>
> *If MCP enabled, add MCP table with tool_calls, per-tool success/failure breakdown*
>
> ### What Happened
>
> For each fault that fired, explain what the agent did:
> - **[scenario-name] ([fault kind]):** [What happened — did the agent crash, retry, succeed, loop?]
> - ...
>
> Cross-reference the proxy logs (verbose output) and the agent's behavior (did runs succeed or fail?) to determine this.
>
> ### Issues Found
>
> List each issue as a numbered item with severity. **Only list issues that actually manifested** — don't speculate about faults that didn't fire.
>
> | # | Issue | Severity | Evidence |
> |---|-------|----------|----------|
> | 1 | [description] | High/Medium/Low | [what happened — e.g., "Run 1 crashed with JSONDecodeError on empty response"] |
> | 2 | ... | ... | ... |
>
> If no issues found (score 80+), say so: "No resilience issues detected. The agent handled all injected faults correctly."
>
> ### Fixes
>
> For each issue, provide a **specific, copy-pasteable fix**. Reference the actual files and code from the codebase (found in Step 2).
>
> **Issue 1: [description]**
> - **File:** `[path/to/file.py]:[line]`
> - **Current code:** `[the relevant line or block]`
> - **Fix:** `[the exact change needed]`
> - **Why:** [one sentence explaining why this fixes the issue]
>
> Common fix patterns:
> - **No retry on errors** → Add `max_retries=3` to the LLM client constructor (`ChatOpenAI(max_retries=3)` or `OpenAI(max_retries=3)`)
> - **No timeout** → Add `request_timeout=30` (or `timeout=30` for raw OpenAI SDK)
> - **Crashes on malformed responses** → `max_retries` handles this at the SDK level; for framework-level resilience, wrap with try/except
> - **Unbounded retries / loops** → Cap retries with `max_retries` instead of infinite loops; add backoff
> - **MCP tool failures crash agent** → Add error handling around tool call results in the agent loop
>
> ### Next Steps
>
> End with a clear call to action:
> - If issues were found: "Want me to apply these fixes now?"
> - If score improved from a previous run: "Score improved from [old] → [new]. [Summary of what fixed it]."
> - If score is 80+: "Your agent is resilient. Consider adding these scenarios to CI to catch regressions."
> - If score is still low after fixes: "Consider re-running with `agentbreak serve` to verify the fixes work."

---

**Then use `AskUserQuestion`** with options based on the results:
- If issues found: "Apply these fixes now" / "Re-run the test" / "I'll handle it myself"
- If all passing: "Add to CI" / "Run with different scenarios" / "Done"

**If the user says "Apply these fixes"**, go ahead and edit the code files directly — you have all the information from Step 2 (codebase scan) and this report to make the changes. After applying, suggest re-running the test to verify.

## Scorecard fields reference

| Field | Meaning |
|-------|---------|
| `requests_seen` | Total requests proxied |
| `injected_faults` | Faults AgentBreak injected |
| `latency_injections` | Latency delays added |
| `upstream_successes` | Requests that succeeded |
| `upstream_failures` | Requests that failed |
| `duplicate_requests` | Same request body seen 2+ times |
| `suspected_loops` | Same body 3+ times (agent may be stuck) |
| `response_mutations` | Response payload mutations applied |
| `run_outcome` | PASS, DEGRADED, or FAIL |
| `resilience_score` | 0-100 |

MCP scorecard adds: `tool_calls`, `tool_call_counts`, `tool_successes_by_name`, `tool_failures_by_name`, `method_counts`.

## Scenario schema reference

### Fault kinds

| Kind | Effect | Target |
|------|--------|--------|
| `http_error` | Returns HTTP error (needs `status_code`) | llm_chat, mcp_tool |
| `latency` | Adds delay (needs `min_ms`, `max_ms`) | llm_chat, mcp_tool |
| `timeout` | Delay + 504 error | **mcp_tool only** |
| `empty_response` | 200 with empty body | llm_chat, mcp_tool |
| `invalid_json` | 200 with unparseable JSON | llm_chat, mcp_tool |
| `schema_violation` | 200 with corrupted structure | llm_chat, mcp_tool |
| `wrong_content` | 200 with replaced content | llm_chat, mcp_tool |
| `large_response` | 200 with oversized body (needs `size_bytes`) | llm_chat, mcp_tool |

### Schedule modes

| Mode | Fields | Behavior |
|------|--------|----------|
| `always` | none | Every matching request faulted |
| `random` | `probability` (0-1) | Probabilistic |
| `periodic` | `every`, `length` | `length` out of every `every` requests |

### Presets

```yaml
preset: brownout              # latency + 429 on LLM
preset: mcp-slow-tools        # latency on MCP
preset: mcp-tool-failures     # 503 on MCP
preset: mcp-mixed-transient   # latency + 503 on MCP
```

## Rules

- **Always determine the LLM provider before generating config.** If ambiguous, ask. Never generate scenarios for both providers — pick one.
- **Never skip review checkpoints.** Use `AskUserQuestion` at every checkpoint so the user gets an interactive prompt. Wrong provider detection leads to wrong endpoints. Wrong scenarios lead to untested failure modes.
- **Complete steps in order.** Each step depends on the previous step's output.
- **Use subagents for codebase scanning** in Step 2. Serial grep is too slow on large codebases.
- **Only show the relevant provider's env vars** in Step 5. If the user uses OpenAI, don't mention Anthropic.
- **In mock mode, no API keys are needed.** Don't ask the user for keys unless they want proxy mode.
- **Always back up and restore `.env`** in Step 5. Never leave the user's config pointing at AgentBreak after testing.
- **If history is enabled, always compare with the previous run in Step 6.** This helps users track whether their changes improved resilience.
- **If you can't trigger the agent programmatically**, use `AskUserQuestion` to ask the user to trigger it manually. Don't just skip the traffic step.

## Common issues

- **Port 5000 in use on macOS**: AirPlay Receiver. Use 5005.
- **MCP inspect fails**: Upstream MCP server must be running first.
- **No faults firing**: Probability too low. Use 0.3+ for visible results.
- **Registry not found**: Run `agentbreak inspect` before `serve` when MCP enabled.
- **No history found**: Enable `history.enabled: true` in `.agentbreak/application.yaml` and re-run.
