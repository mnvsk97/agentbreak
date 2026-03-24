# Examples

## `simple_mcp_server`

MCP server with reporting tools (list sections, fetch KPIs, lookup notes, render briefs). This is the upstream that AgentBreak proxies.

```bash
cd examples/simple_mcp_server
pip install -r requirements.txt
python main.py
```

## `simple_react_agent`

LangGraph ReAct agent that calls an OpenAI-compatible LLM and the MCP server above. Point both URLs at AgentBreak to chaos-test the agent.

```bash
cd examples/simple_react_agent
pip install -r requirements.txt
cp .env.example .env
langgraph dev
```

## `deepagents`

Lightweight ReAct agent built directly on the `openai` SDK (DeepAgents style). No framework beyond the SDK — just a tool-calling loop with retry logic. Point `OPENAI_BASE_URL` at AgentBreak to chaos-test.

```bash
cd examples/deepagents
pip install -r requirements.txt
cp .env.example .env
python agent.py
```

