# Reporting MCP Server Example

This example exposes a small, realistic reporting backend over MCP:

- `list_report_sections`
- `fetch_kpi_snapshot`
- `lookup_account_notes`
- `render_report_brief`

Run it:

```bash
cd examples/reporting_mcp_server
pip install -r requirements.txt
python main.py
```

Default endpoint:

```text
http://127.0.0.1:8001/mcp
```
