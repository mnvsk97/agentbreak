"""
Simple MCP client that demonstrates tool calling and resource reading
through the AgentBreak MCP proxy.

Uses only httpx (already a project dependency) to send JSON-RPC 2.0
requests to the proxy at http://localhost:5001/mcp.

Run the proxy first:
    python -m agentbreak.mcp_proxy --mode mock --fail-rate 0

Then run this script:
    python main.py
"""

from __future__ import annotations

import json
import os
import sys

import httpx

MCP_PROXY_URL = os.getenv("MCP_PROXY_URL", "http://localhost:5001/mcp")
_request_id = 0


def _next_id() -> int:
    global _request_id
    _request_id += 1
    return _request_id


def send_request(method: str, params: dict | None = None) -> dict:
    """Send a single JSON-RPC 2.0 request and return the parsed response."""
    payload = {
        "jsonrpc": "2.0",
        "id": _next_id(),
        "method": method,
    }
    if params is not None:
        payload["params"] = params

    response = httpx.post(MCP_PROXY_URL, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def initialize() -> dict:
    """Send MCP initialize request to negotiate capabilities."""
    return send_request(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "example-mcp-client", "version": "1.0"},
        },
    )


def list_tools() -> list[dict]:
    """Return the list of tools advertised by the server."""
    result = send_request("tools/list")
    if "error" in result:
        raise RuntimeError(f"tools/list error: {result['error']}")
    return result.get("result", {}).get("tools", [])


def call_tool(name: str, arguments: dict | None = None) -> dict:
    """Invoke a named tool and return the raw response."""
    return send_request("tools/call", {"name": name, "arguments": arguments or {}})


def list_resources() -> list[dict]:
    """Return the list of resources advertised by the server."""
    result = send_request("resources/list")
    if "error" in result:
        raise RuntimeError(f"resources/list error: {result['error']}")
    return result.get("result", {}).get("resources", [])


def read_resource(uri: str) -> dict:
    """Read the contents of a resource by URI."""
    return send_request("resources/read", {"uri": uri})


def main() -> None:
    print(f"Connecting to MCP proxy at {MCP_PROXY_URL}")

    # --- Initialization ---
    init_resp = initialize()
    if "error" in init_resp:
        print(f"Initialization failed: {init_resp['error']}", file=sys.stderr)
        sys.exit(1)
    server_info = init_resp.get("result", {}).get("serverInfo", {})
    print(f"Connected to server: {server_info.get('name')} v{server_info.get('version')}")

    # --- List available tools ---
    tools = list_tools()
    print(f"\nAvailable tools ({len(tools)}):")
    for tool in tools:
        print(f"  {tool['name']}: {tool.get('description', '')}")

    # --- Call the 'echo' tool ---
    print("\nCalling tool: echo")
    echo_resp = call_tool("echo", {"text": "hello from agentbreak example"})
    if "error" in echo_resp:
        print(f"  Tool error: {echo_resp['error']}")
    else:
        content = echo_resp.get("result", {}).get("content", [])
        for item in content:
            if item.get("type") == "text":
                print(f"  Result: {item['text']}")

    # --- Call the 'get_time' tool ---
    print("\nCalling tool: get_time")
    time_resp = call_tool("get_time")
    if "error" in time_resp:
        print(f"  Tool error: {time_resp['error']}")
    else:
        content = time_resp.get("result", {}).get("content", [])
        for item in content:
            if item.get("type") == "text":
                print(f"  Result: {item['text']}")

    # --- List available resources ---
    resources = list_resources()
    print(f"\nAvailable resources ({len(resources)}):")
    for resource in resources:
        print(f"  {resource['uri']}: {resource.get('name', '')}")

    # --- Read the first resource ---
    if resources:
        uri = resources[0]["uri"]
        print(f"\nReading resource: {uri}")
        resource_resp = read_resource(uri)
        if "error" in resource_resp:
            print(f"  Resource error: {resource_resp['error']}")
        else:
            contents = resource_resp.get("result", {}).get("contents", [])
            for item in contents:
                print(f"  Content ({item.get('mimeType', 'unknown')}): {item.get('text', '')[:100]}")

    # --- Check scorecard ---
    scorecard_url = MCP_PROXY_URL.replace("/mcp", "/_agentbreak/mcp/scorecard")
    scorecard_resp = httpx.get(scorecard_url, timeout=10)
    if scorecard_resp.status_code == 200:
        scorecard = scorecard_resp.json()
        print(f"\nScorecard: {scorecard['run_outcome']} (score {scorecard['resilience_score']}/100)")
        print(f"  Requests: {scorecard['requests_seen']}, Faults injected: {scorecard['injected_faults']}")


if __name__ == "__main__":
    main()
