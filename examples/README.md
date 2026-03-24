# Examples

## `simple_langchain`

Small OpenAI-compatible client example.

```bash
cd examples/simple_langchain
pip install -r requirements.txt
OPENAI_API_KEY=dummy OPENAI_BASE_URL=http://127.0.0.1:5000/v1 python main.py
```

## `langgraph_report_agent`

LangGraph local-server example using `create_react_agent`, an OpenAI-compatible model, and MCP-backed tools.

```bash
cd examples/langgraph_report_agent
pip install -r requirements.txt
cp .env.example .env
langgraph dev
```

## `simple_mcp_server`

Small FastMCP server with three tools.

```bash
cd examples/simple_mcp_server
pip install -r requirements.txt
python main.py
```

Then in another terminal:

```bash
agentbreak inspect --config application.yaml
agentbreak serve --config application.yaml --scenarios scenarios.yaml
```

## `reporting_mcp_server`

More realistic MCP demo server for report generation. It exposes tools, resources, and a prompt.

```bash
cd examples/reporting_mcp_server
pip install -r requirements.txt
python main.py
```

## `live_harness`

Full live end-to-end run covering direct and AgentBreak-backed LangGraph execution.

```bash
agentbreak verify --live
```
