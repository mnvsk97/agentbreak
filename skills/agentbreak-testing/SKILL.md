---
name: agentbreak-testing
description: Run chaos tests against an OpenAI-compatible app or MCP server using AgentBreak. Uses application.yaml + scenarios.yaml, agentbreak serve, optional MCP inspect, and scorecard endpoints.
---

# AgentBreak Testing

Use this skill to run chaos tests against an OpenAI-compatible app and/or MCP traffic with AgentBreak.

## How it works

- **Mock LLM** (`llm.mode: mock`): AgentBreak returns synthetic completions unless a scenario injects a fault. No API key needed.
- **Proxy LLM** (`llm.mode: proxy`): AgentBreak forwards `/v1/chat/completions` to `llm.upstream_url` when no fault fires.
- **MCP** (`mcp.enabled: true`): Run `agentbreak inspect` once to write `.agentbreak/registry.json`, then `serve` mirrors MCP through AgentBreak with scenario-driven faults.

## Workflow

1. Create config files:

   ```bash
   cp config.example.yaml application.yaml
   cp scenarios.example.yaml scenarios.yaml
   ```

2. Edit `application.yaml`:
   - Mock: `llm.mode: mock`
   - Proxy: `llm.mode: proxy`, set `llm.upstream_url` and `llm.auth`
   - MCP off: `mcp.enabled: false`
   - MCP on: `mcp.enabled: true`, set `mcp.upstream_url` and `mcp.auth`

3. Edit `scenarios.yaml` (or use a preset):

   ```yaml
   version: 1
   scenarios:
     - name: flaky-llm
       summary: Random 429s on chat completions
       target: llm_chat
       match: {}
       fault:
         kind: http_error
         status_code: 429
       schedule:
         mode: random
         probability: 0.3
   ```

   Or just use a preset:

   ```yaml
   version: 1
   preset: brownout
   ```

4. Install:

   ```bash
   pip install -e '.[dev]'
   ```

5. If MCP is enabled, generate the registry:

   ```bash
   agentbreak inspect --config application.yaml
   ```

6. Validate before serving:

   ```bash
   agentbreak validate --config application.yaml --scenarios scenarios.yaml
   ```

7. Serve:

   ```bash
   agentbreak serve --config application.yaml --scenarios scenarios.yaml
   # Add -v / --verbose for debug logging
   ```

8. Point the target app at AgentBreak:

   ```bash
   export OPENAI_BASE_URL=http://127.0.0.1:5000/v1
   export OPENAI_API_KEY=dummy   # use a real key in proxy mode
   ```

9. Run the workload:

   ```bash
   python examples/simple_langchain/main.py
   ```

10. Check results:

    ```bash
    curl http://127.0.0.1:5000/_agentbreak/scorecard
    curl http://127.0.0.1:5000/_agentbreak/requests
    curl http://127.0.0.1:5000/_agentbreak/mcp-scorecard
    curl http://127.0.0.1:5000/_agentbreak/mcp-requests
    ```

11. Summarize: requests seen, injected faults, duplicates, suspected loops, run outcome, resilience score. Treat duplicate/loop counters as signals -- some frameworks legitimately repeat completions.

## Scenario reference

Targets: `llm_chat`, `mcp_tool`.

Fault kinds: `http_error`, `latency`, `timeout`, `empty_response`, `invalid_json`, `schema_violation`, `wrong_content`, `large_response`.

Schedule modes: `always`, `random` (with `probability`), `periodic` (with `every` and `length`).

Match fields (all optional): `tool_name`, `tool_name_pattern` (glob), `route`, `method`, `model`.

Presets: `brownout`, `mcp-slow-tools`, `mcp-tool-failures`, `mcp-mixed-transient`.

## Verification

```bash
agentbreak verify
agentbreak verify --live   # full LangGraph + mock OpenAI + MCP stack
```

## Notes

- There is no `agentbreak start`. Use `agentbreak serve` with YAML configs.
- Scenario names and fault kinds live in `scenarios.yaml`, not CLI flags.
- Default file paths: `application.yaml`, `scenarios.yaml`, `.agentbreak/registry.json`.
- Config file must exist -- `serve` and `validate` raise `FileNotFoundError` if missing.
- Port comes from `serve.port` in `application.yaml` (default 5000).
- Use `--verbose / -v` on `serve` for debug-level logging.
- Ctrl+C prints a resilience scorecard summary to stderr.
