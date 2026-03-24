"""MCP server — HTTP basic authentication.

Rejects requests without valid Authorization: Basic <base64> header.

application.yaml:
  mcp:
    enabled: true
    upstream_url: http://127.0.0.1:8003/mcp
    auth:
      type: basic
      username: agent
      password_env: MCP_PASSWORD
"""
from __future__ import annotations

import base64
import os, socket, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from tools import register_tools


def find_free_port(preferred: int) -> int:
    """Return preferred port if available, otherwise find a free one."""
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


HOST = os.getenv("MCP_HOST", "127.0.0.1")
PORT = find_free_port(int(os.getenv("MCP_PORT", "8003")))
PATH = os.getenv("MCP_PATH", "/mcp")
USERNAME = os.getenv("MCP_USERNAME", "agent")
PASSWORD = os.getenv("MCP_PASSWORD", "test-password")

mcp = FastMCP(name="reporting-mcp-basic", version="0.1.0")
register_tools(mcp)

_expected = "Basic " + base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(PATH):
            auth = request.headers.get("authorization", "")
            if auth != _expected:
                return JSONResponse(status_code=401, content={"error": "Invalid or missing basic credentials"})
        return await call_next(request)


app = mcp.http_app(transport="streamable-http", path=PATH)
app.add_middleware(BasicAuthMiddleware)

if __name__ == "__main__":
    import uvicorn
    print(f"[basic-auth] http://{HOST}:{PORT}{PATH}  user={USERNAME}", flush=True)
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
