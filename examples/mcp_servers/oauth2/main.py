"""MCP server + OAuth2 token endpoint (client_credentials).

Runs two services:
  - /oauth/token  — issues access tokens given client_id + client_secret
  - /mcp          — MCP server, requires Authorization: Bearer <token>

application.yaml:
  mcp:
    enabled: true
    upstream_url: http://127.0.0.1:8004/mcp
    auth:
      type: oauth2_client_credentials
      token_url: http://127.0.0.1:8004/oauth/token
      client_id: my-agent
      client_secret_env: MCP_CLIENT_SECRET
"""
from __future__ import annotations

import json
import os, socket, sys, secrets, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
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
PORT = find_free_port(int(os.getenv("MCP_PORT", "8004")))
PATH = os.getenv("MCP_PATH", "/mcp")
CLIENT_ID = os.getenv("MCP_CLIENT_ID", "my-agent")
CLIENT_SECRET = os.getenv("MCP_CLIENT_SECRET", "test-client-secret")
TOKEN_TTL = int(os.getenv("MCP_TOKEN_TTL", "3600"))

mcp = FastMCP(name="reporting-mcp-oauth2", version="0.1.0")
register_tools(mcp)

# Simple in-memory token store: token -> expiry timestamp
_active_tokens: dict[str, float] = {}


async def issue_token(request: Request) -> Response:
    body = await request.body()
    # Parse form data manually
    from urllib.parse import parse_qs
    form = parse_qs(body.decode("utf-8"))
    grant_type = form.get("grant_type", [None])[0]
    cid = form.get("client_id", [None])[0]
    csecret = form.get("client_secret", [None])[0]

    if grant_type != "client_credentials":
        return JSONResponse(status_code=400, content={"error": "unsupported_grant_type"})
    if cid != CLIENT_ID or csecret != CLIENT_SECRET:
        return JSONResponse(status_code=401, content={"error": "invalid_client"})
    token = secrets.token_hex(32)
    _active_tokens[token] = time.time() + TOKEN_TTL
    print(f"[oauth2] issued token {token[:8]}... ttl={TOKEN_TTL}s", flush=True)
    return JSONResponse(content={"access_token": token, "token_type": "bearer", "expires_in": TOKEN_TTL})


class OAuthBearerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(PATH):
            auth = request.headers.get("authorization", "")
            token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
            expiry = _active_tokens.get(token, 0)
            if not token or time.time() > expiry:
                return JSONResponse(status_code=401, content={"error": "invalid_token"})
        return await call_next(request)


app = mcp.http_app(transport="streamable-http", path=PATH)
app.add_middleware(OAuthBearerMiddleware)
# Add the token endpoint route before the MCP routes
app.routes.insert(0, Route("/oauth/token", issue_token, methods=["POST"]))

if __name__ == "__main__":
    import uvicorn
    print(f"[oauth2] http://{HOST}:{PORT}{PATH}  token_endpoint=/oauth/token  client_id={CLIENT_ID}", flush=True)
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
