"""MCP server — bearer token authentication.

Rejects requests without Authorization: Bearer <token>.

application.yaml:
  mcp:
    enabled: true
    upstream_url: http://127.0.0.1:8002/mcp
    auth:
      type: bearer
      env: MCP_BEARER_TOKEN
"""
from __future__ import annotations

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
PORT = find_free_port(int(os.getenv("MCP_PORT", "8002")))
PATH = os.getenv("MCP_PATH", "/mcp")
TOKEN = os.getenv("MCP_BEARER_TOKEN", "test-bearer-token")

mcp = FastMCP(name="reporting-mcp-bearer", version="0.1.0")
register_tools(mcp)


class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(PATH):
            auth = request.headers.get("authorization", "")
            if auth != f"Bearer {TOKEN}":
                return JSONResponse(status_code=401, content={"error": "Invalid or missing bearer token"})
        return await call_next(request)


app = mcp.http_app(transport="streamable-http", path=PATH)
app.add_middleware(BearerAuthMiddleware)

if __name__ == "__main__":
    import uvicorn
    print(f"[bearer-auth] http://{HOST}:{PORT}{PATH}  token={TOKEN[:8]}...", flush=True)
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
