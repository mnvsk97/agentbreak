# Simple MCP Server Example

This example starts a FastMCP server on:

```text
http://127.0.0.1:8001/mcp
```

Tools:

- `echo_text`
- `add_numbers`
- `get_weather`

Run it:

```bash
pip install -r requirements.txt
python main.py
```

Then point `application.yaml` at `http://127.0.0.1:8001/mcp`, run `agentbreak inspect`, and start `agentbreak serve`.
