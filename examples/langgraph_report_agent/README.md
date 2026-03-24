# LangGraph Report Agent

This example runs a `create_react_agent` graph behind `langgraph dev`.

It uses:

- an OpenAI-compatible chat endpoint
- an MCP server with reporting tools

Quick start:

```bash
cd examples/langgraph_report_agent
pip install -r requirements.txt
cp .env.example .env
langgraph dev
```

The assistant id exposed by `langgraph.json` is:

```text
agent
```

The full live workflow, including AgentBreak in the middle, is automated by:

```bash
python examples/live_harness/run_live_e2e.py
```
