# AgentBreak

Your agent works great — until the LLM times out, returns garbage, or an MCP tool fails. AgentBreak lets you test for that *before* production.

It's a chaos proxy that sits between your agent and the real API, injecting faults like latency spikes, HTTP errors, and malformed responses so you can see how your agent actually handles failure.

```
Agent  -->  AgentBreak (localhost:5005)  -->  Real LLM / MCP server
                     ^
          injects faults based on your scenarios
```

## Get started

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

Available presets: `standard`, `standard-mcp`, `standard-all`, `brownout`, `mcp-slow-tools`, `mcp-tool-failures`, `mcp-mixed-transient`.

New compact planning presets: `deploy-risk`, `retry-resilience`, `incident-replay`.

## MCP testing

```bash
agentbreak inspect    # discover tools from your MCP server
agentbreak serve      # proxy both LLM and MCP traffic
agentbreak recommend  # suggest what to test next
agentbreak incident-replay --text "..."   # turn an incident into scenarios
agentbreak synthesize --run-id 1          # summarize what broke
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

## Claude Code

AgentBreak works as a plugin for [Claude Code](https://docs.anthropic.com/en/docs/claude-code):

```bash
pip install agentbreak
```

Then in Claude Code:

```
/plugin marketplace add mnvsk97/agentbreak
/plugin install agentbreak@mnvsk97-agentbreak
/reload-plugins
```

Three commands:

| Command | What it does |
|---------|-------------|
| `/agentbreak:init` | Analyze codebase, configure mock/proxy mode |
| `/agentbreak:create-tests` | Generate project-specific chaos scenarios |
| `/agentbreak:run-tests` | Run tests, produce resilience report with fixes |

**Update to latest:**

```
/plugin marketplace add mnvsk97/agentbreak
/plugin install agentbreak@mnvsk97-agentbreak
/reload-plugins
```

**Uninstall:**

```
/plugin uninstall agentbreak@mnvsk97-agentbreak
/reload-plugins
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

## Full reference

For the full list of fault kinds, schedule modes, match filters, and config options, see the [documentation](https://mnvsk97.github.io/agentbreak).

## Roadmap

- ~~**Security scenarios** — prompt injection, data exfiltration attempts, and adversarial inputs~~ Done (tool poisoning)
- ~~**MCP server chaos** — tool call validation, schema mismatches, and poisoned tool responses~~ Done (tool poisoning + rug pull)
- **Pattern-based attacks** — multi-step attack chains that exploit common agent reasoning patterns
- **Skill-based attacks** — target agent skills/capabilities with adversarial tool sequences
- **Deprecated library injection** — return responses referencing deprecated or vulnerable libraries
- **Model deprecation simulation** — simulate model sunset responses and version migration failures
