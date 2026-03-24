# Simple ReAct Agent (LangGraph)

LangGraph ReAct agent that uses an OpenAI-compatible LLM and MCP reporting tools.

## Setup

```bash
cd examples/agents/simple_react_agent
pip install -r requirements.txt
cp .env.example .env
langgraph dev
```

## Chaos testing

Point both URLs at AgentBreak:

```env
OPENAI_BASE_URL=http://127.0.0.1:5005/v1
REPORT_MCP_URL=http://127.0.0.1:5005/mcp
```
