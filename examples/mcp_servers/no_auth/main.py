"""MCP server — no authentication."""
from __future__ import annotations

import os, socket, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastmcp import FastMCP
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
PORT = find_free_port(int(os.getenv("MCP_PORT", "8001")))
PATH = os.getenv("MCP_PATH", "/mcp")

mcp = FastMCP(name="reporting-mcp-noauth", version="0.1.0")
register_tools(mcp)

if __name__ == "__main__":
    print(f"[no-auth] http://{HOST}:{PORT}{PATH}", flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, path=PATH)
