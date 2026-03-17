"""
Demonstrates retry logic for MCP tool calls through the AgentBreak proxy.

When AgentBreak injects faults, a well-written MCP client should retry
transient errors (rate limits, server errors) but NOT retry permanent
errors (invalid request, method not found).

Run the proxy with fault injection first:
    python -m agentbreak.mcp_proxy --mode mock --fail-rate 0.3 --seed 42

Then run this script:
    python retry_example.py
"""

from __future__ import annotations

import os
import sys
import time

import httpx

MCP_PROXY_URL = os.getenv("MCP_PROXY_URL", "http://localhost:5001/mcp")

# JSON-RPC error codes that are worth retrying (transient failures).
RETRYABLE_CODES = {
    -32000,  # MCP_TOOL_ERROR (rate limit, tool crash)
    -32603,  # INTERNAL_ERROR (server-side failure)
}

# JSON-RPC error codes that should NOT be retried (permanent failures).
PERMANENT_CODES = {
    -32700,  # Parse error
    -32600,  # Invalid request
    -32601,  # Method not found
    -32602,  # Invalid params
}

_request_id = 0


def _next_id() -> int:
    global _request_id
    _request_id += 1
    return _request_id


def send_request(method: str, params: dict | None = None) -> dict:
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


def call_tool_with_retry(
    name: str,
    arguments: dict | None = None,
    max_attempts: int = 5,
    backoff_seconds: float = 1.0,
) -> dict:
    """
    Call an MCP tool with exponential-backoff retry on transient errors.

    Raises RuntimeError if all attempts are exhausted or a permanent error occurs.
    """
    attempt = 0
    delay = backoff_seconds
    while attempt < max_attempts:
        attempt += 1
        print(f"  Attempt {attempt}/{max_attempts} for tool '{name}'...")
        result = send_request("tools/call", {"name": name, "arguments": arguments or {}})

        if "error" not in result:
            return result

        error = result["error"]
        code = error.get("code")
        message = error.get("message", "")

        if code in PERMANENT_CODES:
            raise RuntimeError(f"Permanent MCP error {code}: {message}")

        if code in RETRYABLE_CODES:
            if attempt < max_attempts:
                print(f"  Transient error {code}: {message} — retrying in {delay:.1f}s")
                time.sleep(delay)
                delay = min(delay * 2, 30.0)
                continue
            raise RuntimeError(f"Exhausted {max_attempts} attempts. Last error {code}: {message}")

        # Unknown error code — treat as permanent to avoid infinite loops.
        raise RuntimeError(f"Unknown MCP error {code}: {message}")

    raise RuntimeError(f"Exhausted {max_attempts} attempts without success.")


def read_resource_with_retry(
    uri: str,
    max_attempts: int = 3,
    backoff_seconds: float = 1.0,
) -> dict:
    """
    Read an MCP resource with retry on transient errors.
    """
    attempt = 0
    delay = backoff_seconds
    while attempt < max_attempts:
        attempt += 1
        print(f"  Attempt {attempt}/{max_attempts} for resource '{uri}'...")
        result = send_request("resources/read", {"uri": uri})

        if "error" not in result:
            return result

        error = result["error"]
        code = error.get("code")
        message = error.get("message", "")

        if code in PERMANENT_CODES:
            raise RuntimeError(f"Permanent MCP error {code}: {message}")

        if attempt < max_attempts:
            print(f"  Transient error {code}: {message} — retrying in {delay:.1f}s")
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
            continue

        raise RuntimeError(f"Exhausted {max_attempts} attempts. Last error {code}: {message}")

    raise RuntimeError(f"Exhausted {max_attempts} attempts without success.")


def main() -> None:
    print(f"MCP retry example — proxy at {MCP_PROXY_URL}")
    print("(Start the proxy with --fail-rate 0.3 to see retries in action)\n")

    # Initialize
    init_result = send_request(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "retry-example", "version": "1.0"},
        },
    )
    if "error" in init_result:
        print(f"Initialization failed: {init_result['error']}", file=sys.stderr)
        sys.exit(1)
    print("Initialized successfully.\n")

    # --- Tool call with retry ---
    print("Calling tool 'echo' with retry logic:")
    try:
        result = call_tool_with_retry("echo", {"text": "resilience test"}, max_attempts=5)
        content = result.get("result", {}).get("content", [])
        text = next((i["text"] for i in content if i.get("type") == "text"), "(no text)")
        print(f"  Success: {text}\n")
    except RuntimeError as exc:
        print(f"  All retries failed: {exc}\n")

    # --- Resource read with retry ---
    print("Reading resource 'file:///example/readme.txt' with retry logic:")
    try:
        result = read_resource_with_retry("file:///example/readme.txt", max_attempts=3)
        contents = result.get("result", {}).get("contents", [])
        text = next((i["text"] for i in contents if "text" in i), "(no content)")
        print(f"  Success: {text[:80]}\n")
    except RuntimeError as exc:
        print(f"  All retries failed: {exc}\n")

    # --- Scorecard ---
    scorecard_url = MCP_PROXY_URL.replace("/mcp", "/_agentbreak/mcp/scorecard")
    scorecard_resp = httpx.get(scorecard_url, timeout=10)
    if scorecard_resp.status_code == 200:
        sc = scorecard_resp.json()
        print(f"Final scorecard: {sc['run_outcome']} (score {sc['resilience_score']}/100)")
        print(f"  Requests: {sc['requests_seen']}, Faults injected: {sc['injected_faults']}")
        print(f"  Duplicate requests (loops): {sc['duplicate_requests']}")


if __name__ == "__main__":
    main()
