# Live Testing

AgentBreak now includes a repeatable live harness for end-to-end validation with:

- a deterministic OpenAI-compatible mock model
- a realistic reporting MCP server
- a LangGraph `create_react_agent` server launched with `langgraph dev`
- AgentBreak inserted between the agent and its upstreams

Run it from the repo root:

```bash
agentbreak verify --live
```

What it does:

1. Starts the mock OpenAI server and reporting MCP server.
2. Launches the LangGraph server directly against those upstreams.
3. Sends a request through the LangGraph SDK and saves the baseline result.
4. Stops LangGraph, runs `agentbreak inspect`, and starts AgentBreak.
5. Restarts LangGraph pointing at AgentBreak for both LLM and MCP traffic.
6. Sends the same request again and saves the chaos-backed result plus AgentBreak scorecard artifacts.

Artifacts are written to:

```text
/tmp/agentbreak-live/<timestamp>/
```

Key files:

- `run.log`
- `mock-openai.log`
- `reporting-mcp.log`
- `agentbreak.log`
- `langgraph.log`
- `artifacts/direct-response.json`
- `artifacts/chaos-response.json`
- `artifacts/agentbreak-llm-scorecard.json`
- `artifacts/agentbreak-llm-requests.json`
- `artifacts/agentbreak-mcp-scorecard.json`
- `artifacts/agentbreak-mcp-requests.json`
- `artifacts/registry.json`
- `artifacts/effective-application.yaml`
- `artifacts/effective-scenarios.yaml`
