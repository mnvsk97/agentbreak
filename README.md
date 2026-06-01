# AgentBreak

AgentBreak lets coding agents test LLM apps for resilience through plain English.

## Install

```bash
npx skills add mnvsk97/agentbreak --skill agent-resilience-testing --yes
```

Then open your coding agent in the project you want to test and say:

```text
Test my agent for resilience.
```

The skill analyzes the repo, checks or installs the AgentBreak CLI, configures mock or proxy mode, generates scenarios, runs resilience checks, and returns a report with findings and fixes.

## What It Tests

The skill always covers four lanes:

- **LLM failures** — outages, brownouts, rate limits, context limits, malformed outputs, streaming failures, and prompt injection
- **Agent skill supply chain** — malicious or over-broad skills, unsafe downloads, secret access, exfiltration, and dangerous commands
- **Guardrails** — input/output checks, tool-argument validation, tool-result sanitization, PII/secrets redaction, and approval gates
- **MCP servers/tools** — transport failures, bad schemas, bad results, registry drift, rug pulls, poisoning, and cross-tool attacks

## CLI Engine

The skill uses the Python CLI as the reliable engine for proxying, fault injection, MCP inspection, scorecards, and history. You can also run the CLI directly:

```bash
pip install agentbreak
agentbreak init       # creates .agentbreak/ with default configs
agentbreak serve      # start the chaos proxy on port 5005
```

Point your agent at `http://localhost:5005` instead of the real API:

```bash
# OpenAI
export OPENAI_BASE_URL=http://localhost:5005/v1

# Anthropic
export ANTHROPIC_BASE_URL=http://localhost:5005
```

Run your agent, then check how it did:

```bash
curl localhost:5005/_agentbreak/scorecard
```

That's it. No code changes needed — just swap the base URL.

## How it works

AgentBreak reads two files from `.agentbreak/`:

- **`application.yaml`** — what to proxy (LLM mode, MCP upstream, port)
- **`scenarios.yaml`** — what faults to inject

### Fault catalog

AgentBreak ships with 10 built-in fault types across two categories:

**Reliability** — HTTP errors, latency, timeouts, empty responses, invalid JSON, schema violations, wrong content, large responses

**Security** — tool poisoning (prompt injection, exfiltration, cross-tool manipulation, many-shot jailbreaks), rug pulls (tool definitions that mutate after N requests)

Each fault is defined as YAML in `agentbreak/faults/catalog/`. Adding a new fault is just a folder + `manifest.yaml` — no Python required for most faults.

### Scenarios

A scenario is just a target + a fault + a schedule:

```yaml
scenarios:
  - name: slow-llm
    summary: Latency spike on completions
    target: llm_chat          # what to hit (llm_chat or mcp_tool)
    fault:
      kind: latency           # what goes wrong
      min_ms: 2000
      max_ms: 5000
    schedule:
      mode: random            # when it happens
      probability: 0.3
```

Don't want to write YAML? Use a preset:

```yaml
preset: brownout
```

Available presets:

| Preset | Focus |
|--------|-------|
| `standard` | Common LLM failures (rate limits, 500s, latency, bad JSON, empty/invalid responses) |
| `standard-mcp` | Common MCP tool failures (503s, timeouts, latency, empty/invalid/garbage responses) |
| `standard-all` | Everything in `standard` + `standard-mcp` |
| `brownout` | Intermittent LLM latency and rate limits |
| `mcp-slow-tools` | Heavy latency on MCP tool calls |
| `mcp-tool-failures` | MCP transport failures (503s) |
| `mcp-mixed-transient` | Intermittent MCP latency + transport failures |
| `mcp-security` | MCP prompt injection, exfiltration, cross-tool, many-shot, and rug pulls |
| `injection-suite` | Prompt-injection surface sweep — encoding evasion and invisible text on LLM output, plus indirect injection, tool-description poisoning, and cross-server shadowing on MCP tools |

## MCP testing

```bash
agentbreak inspect    # discover tools from your MCP server
agentbreak serve      # proxy both LLM and MCP traffic
```

## Track resilience over time

```yaml
# in .agentbreak/application.yaml
history:
  enabled: true
```

```bash
agentbreak serve --label "added retry logic"
agentbreak history compare 1 2    # diff two runs
```

## What it actually measures

AgentBreak doesn't score you on whether faults happen — it injected those on purpose. It scores **what your agent does after the fault** — both reliability failures (retries, error handling) and security failures (following poisoned instructions, leaking data).

```
Agent sends request  →  AgentBreak injects 500 error  →  Agent retries  →  Success
                                                          ^^^^^^^^^^^^^^^^^^^^^^^^
                                                          This is what gets scored
```

- Agent retries and succeeds → recovery (+5)
- Agent gives up after one failure → upstream failure (-12)
- Agent retries the same thing 20 times → suspected loop (-10)

When you run through mock mode with direct curl, there's no agent in the loop — so there's nothing to evaluate beyond confirming faults fire. The real value comes from running in proxy mode through your actual agent, where its retry logic, error handling, and framework behavior all get exercised.

## CI/CD

Run chaos tests in your pipeline using mock mode — no API keys needed.

**GitHub Actions:**

```yaml
- name: Chaos test
  run: |
    pip install agentbreak
    agentbreak init
    agentbreak serve &
    sleep 2

    # send test traffic
    for i in $(seq 1 10); do
      curl -s http://localhost:5005/v1/chat/completions \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer dummy" \
        -d "{\"model\":\"gpt-4o\",\"messages\":[{\"role\":\"user\",\"content\":\"test $i\"}]}" &
    done
    wait

    # check score — fail the build if below threshold
    SCORE=$(curl -s http://localhost:5005/_agentbreak/scorecard | python3 -c "import sys,json; print(json.load(sys.stdin)['score'])")
    echo "Resilience score: $SCORE"
    pkill -f "agentbreak serve" || true
    python3 -c "exit(0 if $SCORE >= 60 else 1)"
```

For proxy mode (real API traffic), set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` as a repository secret and configure `.agentbreak/application.yaml` with `mode: proxy`.

Commit your `.agentbreak/application.yaml` and `.agentbreak/scenarios.yaml` to the repo so CI uses the same config.

## Reference

### Common commands

```bash
agentbreak init                         # create .agentbreak/
agentbreak validate                     # validate application.yaml and scenarios.yaml
agentbreak validate --test-connection   # also check upstream auth/connectivity
agentbreak inspect                      # discover MCP tools, resources, and prompts
agentbreak serve                        # start the proxy
agentbreak history list                 # show saved runs when history is enabled
agentbreak history compare 1 2          # compare two saved runs
```

### Scenario fields

| Field | Purpose |
|-------|---------|
| `target` | `llm_chat` or `mcp_tool` |
| `fault.kind` | Fault to inject |
| `schedule.mode` | `always`, `random`, or `periodic` |
| `match.model` | Scope an LLM fault to one model |
| `match.tool_name` | Scope an MCP fault to one tool |
| `match.tool_name_pattern` | Scope MCP faults with a wildcard, like `search_*` |

### Built-in fault kinds

| Fault | What it does |
|-------|--------------|
| `http_error` | Returns an HTTP error |
| `latency` | Adds delay |
| `timeout` | Delays then returns 504 for MCP |
| `empty_response` | Returns an empty body |
| `invalid_json` | Returns malformed JSON |
| `schema_violation` | Corrupts response shape |
| `wrong_content` | Replaces content |
| `large_response` | Returns oversized output |
| `tool_poisoning` | Injects adversarial content into MCP tool results |
| `rug_pull` | Mutates tool definitions after N requests |

## Roadmap

- ~~**Security scenarios** — prompt injection, data exfiltration attempts, and adversarial inputs~~ Done (tool poisoning)
- ~~**MCP server chaos** — tool call validation, schema mismatches, and poisoned tool responses~~ Done (tool poisoning + rug pull)
- **Pattern-based attacks** — multi-step attack chains that exploit common agent reasoning patterns
- **Skill-based attacks** — target agent skills/capabilities with adversarial tool sequences
- **Deprecated library injection** — return responses referencing deprecated or vulnerable libraries
- **Model deprecation simulation** — simulate model sunset responses and version migration failures
