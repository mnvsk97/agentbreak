# Testing Methodology

How to design effective chaos tests and read results.

## Start simple

Begin with one fault at a time. A single `http_error 500` on `always` schedule tells you whether the agent retries, crashes, or gives up.

```yaml
scenarios:
  - name: llm-always-500
    summary: Every LLM call fails
    target: llm_chat
    fault:
      kind: http_error
      status_code: 500
    schedule:
      mode: always
```

## Add realism with schedules

Real failures are intermittent. Use `random` with a probability, or `periodic` for burst patterns.

```yaml
schedule:
  mode: random
  probability: 0.3     # 30% of requests fail
```

```yaml
schedule:
  mode: periodic
  every: 5             # every 5th request...
  length: 2            # ...2 consecutive requests fail
```

## Combine faults

Layer multiple scenarios. A brownout might mean slow responses *and* occasional errors:

```yaml
scenarios:
  - name: slow-llm
    summary: LLM latency spikes
    target: llm_chat
    fault:
      kind: latency
      min_ms: 3000
      max_ms: 8000
    schedule:
      mode: random
      probability: 0.4

  - name: llm-rate-limit
    summary: Occasional rate limits
    target: llm_chat
    fault:
      kind: http_error
      status_code: 429
    schedule:
      mode: random
      probability: 0.2
```

## Target specific tools or models

Use the `match` field to scope faults:

```yaml
match:
  model: gpt-4o          # only affect requests to this model
```

```yaml
match:
  tool_name: search_docs  # only affect this MCP tool
```

```yaml
match:
  tool_name_pattern: "search_*"  # wildcard matching
```

## Reading results

### Scorecard

After a test run, check the scorecard:

```bash
curl localhost:5005/_agentbreak/scorecard
```

Key metrics:

| Metric | Meaning |
|--------|---------|
| `requests_seen` | Total requests the agent made |
| `injected_faults` | How many faults AgentBreak applied |
| `upstream_successes` | Requests that got a valid response |
| `upstream_failures` | Failed requests (injected + real) |
| `duplicate_requests` | Same payload sent twice |
| `suspected_loops` | Same payload sent 3+ times |
| `resilience_score` | 0-100 composite score |
| `run_outcome` | `PASS`, `DEGRADED`, or `FAIL` |

### Run outcome

- **PASS** — no failures, no loops. The agent handled everything cleanly.
- **DEGRADED** — some failures occurred, but some requests succeeded. The agent partially recovered.
- **FAIL** — all requests failed, or the agent got stuck in a loop.

## Presets

Built-in scenario bundles for common patterns:

| Preset | What it does |
|--------|-------------|
| `brownout` | Random LLM latency + rate limits |
| `mcp-slow-tools` | 90% of MCP tool calls are slow |
| `mcp-tool-failures` | 30% of MCP tool calls return 503 |
| `mcp-mixed-transient` | Light MCP latency + errors |

```yaml
preset: brownout
```

## Workflow

1. **`agentbreak init`** — generate config files
2. **Edit scenarios** — define what faults to inject
3. **`agentbreak serve`** — start the proxy
4. **Run your agent** — point it at `localhost:5005`
5. **Check scorecard** — review results at `/_agentbreak/scorecard`
6. **Iterate** — adjust scenarios, re-run, compare scores
