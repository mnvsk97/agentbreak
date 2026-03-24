# Examples

## Agents

Example agents that you can point at AgentBreak by swapping env vars.

| Agent | Path | Framework |
|-------|------|-----------|
| Simple ReAct | `agents/simple_react_agent/` | LangGraph |
| DeepAgents-style | `agents/deepagents/` | OpenAI SDK |

## MCP Servers

Example MCP servers with different auth configurations. Use these to test `agentbreak inspect` and MCP proxying with auth.

| Server | Path | Auth | Default port |
|--------|------|------|-------------|
| No auth | `mcp_servers/no_auth/` | None | 8001 |
| Bearer token | `mcp_servers/bearer_auth/` | `Authorization: Bearer <token>` | 8002 |
| Basic auth | `mcp_servers/basic_auth/` | `Authorization: Basic <base64>` | 8003 |
| OAuth2 | `mcp_servers/oauth2/` | Client credentials + bearer | 8004 |

All MCP servers share the same reporting tools (defined in `mcp_servers/tools.py`). Install dependencies once:

```bash
cd examples/mcp_servers
pip install -r requirements.txt
```

Then run any server:

```bash
python mcp_servers/no_auth/main.py
python mcp_servers/bearer_auth/main.py   # set MCP_BEARER_TOKEN
python mcp_servers/basic_auth/main.py    # set MCP_USERNAME, MCP_PASSWORD
python mcp_servers/oauth2/main.py        # set MCP_CLIENT_ID, MCP_CLIENT_SECRET
```
