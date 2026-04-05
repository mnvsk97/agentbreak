---
description: Run chaos tests — inject faults, stress test, and check your agent's resilience to failures
allowed-tools: Read, Glob, Grep, Bash, Edit, Write, AskUserQuestion
---

# AgentBreak -- Run Chaos Tests

You are helping the user run chaos tests against their agent using AgentBreak. AgentBreak is a local proxy that sits between an agent and its LLM/MCP backends, injecting faults defined in `scenarios.yaml`.

```
Agent  →  AgentBreak (localhost)  →  Real LLM / MCP server (or mock)
               ↑
          scenarios.yaml defines faults
```

## Your job

Walk the user through the full workflow: validate, serve, send traffic, read the scorecard. Do not skip steps. If something fails, diagnose and fix it before moving on.

**Choose the right path based on mode:**
- **Mock mode** → use the Quick Smoke Test path (Step 7A). No agent wiring needed.
- **Proxy mode** → use the Full Agent Wiring path (Step 7B). Wire the actual agent.

## Step-by-step instructions

### Step 1: Install AgentBreak

Check if `agentbreak` CLI is available:

```bash
agentbreak --help
```

If not found, detect environment and install:

```bash
which uv 2>/dev/null && echo "HAS_UV=1" || echo "HAS_UV=0"
python3 -c "import sys; print('IN_VENV=1' if sys.prefix != sys.base_prefix else 'IN_VENV=0')" 2>/dev/null
```

- **uv available** → `uv pip install agentbreak`
- **In a venv** → `pip install agentbreak`
- **Neither** → suggest creating a venv first: `python3 -m venv .venv && source .venv/bin/activate && pip install agentbreak`

### Step 2: Create configuration files

If `.agentbreak/application.yaml` and `.agentbreak/scenarios.yaml` don't already exist, initialize them:

```bash
agentbreak init
```

### Step 3: Configure application.yaml

Ask the user what they want to test. Based on their answer, edit `.agentbreak/application.yaml`.

IMPORTANT: On macOS, port 5000 is often taken by AirPlay Receiver. Use port 5005 or another free port.

### Step 4: Configure scenarios.yaml

If the user doesn't have specific scenarios, use the standard preset or configure demo-friendly scenarios.

### Step 5: Validate configuration

Always validate before serving:

```bash
agentbreak validate
```

If validation fails, fix the issue and re-validate.

### Step 5b: Inspect MCP (if enabled)

**Only for proxy mode with `mcp.enabled: true`.** Skip for mock mode.

```bash
agentbreak inspect
```

If this fails (connection refused, auth error, timeout), **do NOT silently disable MCP and continue**. Stop and ask the user:

> "MCP inspect failed: [error details]. Would you like to:
> 1. **Fix it** — check the MCP server URL/token and retry
> 2. **Skip MCP** — disable MCP testing and continue with LLM-only scenarios"

Wait for the user's answer before proceeding. Only disable MCP if they explicitly choose option 2.

### Step 6: Start the chaos proxy

```bash
agentbreak serve -v &
```

Wait for it to be ready:
```bash
sleep 2 && curl -s http://localhost:5005/healthz
```

### Step 7A: Quick Smoke Test (mock mode)

**Use this path when `llm.mode: mock` or `mcp.mode: mock`.** No agent wiring needed — just send requests directly to the proxy.

```bash
for i in {1..10}; do
  curl -s -w "\n" http://localhost:5005/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer dummy" \
    -d "{\"model\":\"gpt-4o\",\"messages\":[{\"role\":\"user\",\"content\":\"Test request $i: What is $(shuf -n1 /usr/share/dict/words 2>/dev/null || echo "test-$i")?\"}]}" &
done
wait
```

If MCP is also in mock mode:
```bash
for i in {1..5}; do
  curl -s -w "\n" http://localhost:5005/mcp \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":$i,\"method\":\"tools/call\",\"params\":{\"name\":\"test_tool\",\"arguments\":{\"query\":\"test $i\"}}}" &
done
wait
```

Check traffic landed:
```bash
curl -s http://localhost:5005/_agentbreak/scorecard | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Requests: {d[\"requests_seen\"]}, Faults: {d[\"injected_faults\"]}')"
```

**IMPORTANT caveat for the report:** When using mock mode with direct curl, the results show raw endpoint resilience — there is no SDK retry logic, no error handling, no agent framework involved. The score will be lower than real-world usage if the agent has retry logic (e.g., `ChatOpenAI(max_retries=3)`). Always note this in the report.

Skip to Step 8 after this.

### Step 7B: Full Agent Wiring (proxy mode)

**Use this path when testing through the actual agent.** This gives the most realistic results because the agent's retry logic, error handling, and framework behavior are all exercised.

#### 7b.1. Find the LLM connection config

Search the codebase for how the agent connects to its LLM:
- `.env` files: look for `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, or custom vars like `TFY_GATEWAY_URL`, `LLM_BASE_URL`
- Code: `base_url=` in SDK constructors, `ChatOpenAI(base_url=...)`, `Anthropic(base_url=...)`
- Config files: YAML/JSON with endpoint URLs

#### 7b.2. Back up and modify `.env`

```bash
cp .env .env.backup
```

Edit `.env` to replace the LLM URL with the AgentBreak proxy:

**If OpenAI / OpenAI-compatible:**
- Change the base URL var (e.g. `OPENAI_BASE_URL`, `TFY_GATEWAY_URL`) to `http://127.0.0.1:5005/v1`
- If mock mode: set the API key to `dummy` (or leave real key — mock mode ignores it)

**If Anthropic:**
- Change the base URL var to `http://127.0.0.1:5005`
- If mock mode: set the API key to `dummy`

**If MCP is also enabled:**
- Change the MCP URL var to `http://127.0.0.1:5005/mcp`

**IMPORTANT:** Many tools (`langgraph dev`, `dotenv`, subprocess launchers) ignore inline env var overrides and only read `.env` files. Always edit the actual `.env` file.

#### 7b.3. Start the agent

Start the agent using its normal run command and wait for it to be ready.

#### 7b.4. Trigger runs through the agent

Send real requests so LLM/MCP traffic flows through AgentBreak. Run **3-5 invocations** with different prompts to avoid loop detection.

#### 7b.5. Verify traffic and restore config

Check that requests flowed through:
```bash
curl -s http://localhost:5005/_agentbreak/scorecard | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Requests: {d[\"requests_seen\"]}, Faults: {d[\"injected_faults\"]}')"
```

**Restore the original config and stop the agent:**
```bash
cp .env.backup .env && rm .env.backup
```

### Step 8: Collect results & produce report

Fetch all scorecard data:

```bash
curl -s http://localhost:5005/_agentbreak/scorecard
curl -s http://localhost:5005/_agentbreak/requests
# If MCP enabled:
curl -s http://localhost:5005/_agentbreak/mcp-scorecard
curl -s http://localhost:5005/_agentbreak/mcp-requests
```

Stop the proxy:
```bash
pkill -f "agentbreak serve" 2>/dev/null || true
```

If history is enabled, compare with previous run:
```bash
agentbreak history
agentbreak history compare <old_id> <new_id>
```

**Now produce the Chaos Test Report.** Use tables throughout so the user can scan results quickly.

---

> ## Chaos Test Report
>
> | | |
> |---|---|
> | **Agent** | [name/path] |
> | **Mode** | [mock / proxy] |
> | **Traffic source** | [Direct curl (raw endpoint) / Through agent (with SDK retry logic)] |
> | **Score** | **[score]/100** — [PASS / DEGRADED / FAIL] |
> | **Scenarios** | [N total] ([N LLM], [N MCP]) |
>
> ---
>
> ### How the score is calculated
>
> Starts at 100, then:
>
> | Event | LLM penalty | MCP penalty |
> |-------|----------:|----------:|
> | Each fault injected | -3 | -5 |
> | Each upstream failure | -12 | -12 |
> | Each duplicate request | -2 | -2 |
> | Each suspected loop | -10 | -10 |
> | Each fault recovery (LLM only) | +5 | — |
>
> Score is clamped to 0–100. Outcome: **PASS** (no upstream failures or loops), **DEGRADED** (some successes), **FAIL** (all failed).
>
> ---
>
> ### 1. Traffic Summary
>
> | Metric | Count | % of Total |
> |--------|------:|----------:|
> | Total requests | [N] | 100% |
> | Faults injected | [N] | [X]% |
> | Clean pass-throughs | [N] | [X]% |
> | Latency injections | [N] | [X]% |
> | Error responses (4xx/5xx) | [N] | [X]% |
> | Response mutations | [N] | [X]% |
> | Duplicate requests | [N] | [X]% |
> | Suspected loops | [N] | [X]% |
>
> *If MCP enabled, add a separate table:*
>
> **MCP Tool Breakdown**
>
> | Tool | Requests | Faults | Successes | Failures |
> |------|---------|--------|-----------|----------|
> | [tool_name] | [N] | [N] | [N] | [N] |
>
> ---
>
> ### 2. Scenario Results
>
> | Scenario | Fault | Target | Fired | Agent Behavior | Verdict |
> |----------|-------|--------|------:|----------------|---------|
> | [scenario-name] | [fault kind] | [llm/mcp] | [N]x | [Recovered / Crashed / Looped / Degraded] | PASS/FAIL |
>
> For each FAIL row, add a one-line explanation below the table:
> - **[scenario-name]:** [what went wrong, with evidence from logs]
>
> ---
>
> ### 3. Issues Found
>
> *If score is 80+ and no issues: "No resilience issues detected."*
>
> | # | Issue | Severity | Scenario | Evidence |
> |--:|-------|----------|----------|----------|
> | 1 | [description] | HIGH | [scenario-name] | [what happened] |
> | 2 | [description] | MEDIUM | [scenario-name] | [what happened] |
> | 3 | [description] | LOW | [scenario-name] | [what happened] |
>
> ---
>
> ### 4. Suggested Fixes
>
> | # | Issue | File | Fix | Why |
> |--:|-------|------|-----|-----|
> | 1 | [description] | `[path:line]` | `[exact code change]` | [one sentence] |
> | 2 | [description] | `[path:line]` | `[exact code change]` | [one sentence] |
>
> ---
>
> ### 5. Testing Caveat
>
> **If traffic source is "Direct curl (raw endpoint)":**
>
> > These results reflect raw HTTP endpoint behavior without SDK retry logic.
> > Your agent uses [detected SDK, e.g. `ChatOpenAI(max_retries=3)`] which would automatically retry transient errors (429, 500, connection errors).
> > To get accurate resilience scores, re-run with `/agentbreak:run-tests` using proxy mode through the actual agent.
>
> **If traffic source is "Through agent":** omit this section.
>
> ---
>
> ### 6. Run Comparison
>
> *If history has a previous run:*
>
> | Metric | Previous | Current | Delta |
> |--------|---------|---------|-------|
> | Score | [old] | [new] | [+/-] |
> | Requests | [old] | [new] | [+/-] |
> | Faults injected | [old] | [new] | [+/-] |
> | Issues | [old] | [new] | [+/-] |
>
> *If no previous run: "First run — no comparison available."*
>
> ---
>
> ### 7. Next Steps
>
> - If score 80+: "Agent is resilient. Consider adding to CI."
> - If issues found: "Apply the fixes above, then re-run `/agentbreak:run-tests` to verify."
> - If tested with raw curl: "For accurate results, re-run through your actual agent in proxy mode."

---

**IMPORTANT:**
- Use tables for every section — no prose walls. The user should be able to scan the report in 30 seconds.
- Every claim must have evidence from the scorecard or logs.
- **Do NOT offer to apply fixes.** Just present findings and suggested fixes. The user decides what to do next.
- **Always include the scoring formula** so the user understands why they got that score.
- **Always note the traffic source.** Raw curl results will overstate issues if the agent has retry logic.
