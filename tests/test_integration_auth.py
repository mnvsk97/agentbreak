"""Integration tests: agentbreak inspect against each MCP server auth variant.

Run with:  pytest -m integration tests/test_integration_auth.py
"""
from __future__ import annotations

import asyncio
import base64
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from agentbreak.config import AuthConfig, MCPConfig
from agentbreak.discovery.mcp import inspect_mcp_server

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVERS_DIR = REPO_ROOT / "examples" / "mcp_servers"


def find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_mcp(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.post(
                url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "clientInfo": {"name": "test", "version": "0.1"},
                    },
                },
                headers={
                    "content-type": "application/json",
                    "accept": "application/json, text/event-stream",
                    "mcp-protocol-version": "2024-11-05",
                    **(headers or {}),
                },
                timeout=2.0,
            )
            if r.status_code < 500:
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"MCP server not ready: {url}")


def _start_server(script: Path, env_overrides: dict[str, str]) -> subprocess.Popen:
    env = {**os.environ, "PYTHONUNBUFFERED": "1", **env_overrides}
    proc = subprocess.Popen(
        [sys.executable, str(script)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc


# ---------------------------------------------------------------------------
# no_auth
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_inspect_no_auth_mcp_server():
    port = find_free_port()
    url = f"http://127.0.0.1:{port}/mcp"
    proc = _start_server(
        SERVERS_DIR / "no_auth" / "main.py",
        {"MCP_PORT": str(port)},
    )
    try:
        wait_for_mcp(url)
        config = MCPConfig(enabled=True, upstream_url=url)
        registry = asyncio.run(inspect_mcp_server(config))
        assert len(registry.tools) == 4, f"Expected 4 tools, got {len(registry.tools)}"
    finally:
        proc.terminate()
        proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# bearer_auth
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_inspect_bearer_auth_mcp_server():
    port = find_free_port()
    token = "test-token-123"
    url = f"http://127.0.0.1:{port}/mcp"
    proc = _start_server(
        SERVERS_DIR / "bearer_auth" / "main.py",
        {"MCP_PORT": str(port), "MCP_BEARER_TOKEN": token},
    )
    try:
        wait_for_mcp(url, headers={"authorization": f"Bearer {token}"})
        config = MCPConfig(
            enabled=True,
            upstream_url=url,
            auth=AuthConfig(type="bearer", token=token),
        )
        registry = asyncio.run(inspect_mcp_server(config))
        assert len(registry.tools) == 4, f"Expected 4 tools, got {len(registry.tools)}"
    finally:
        proc.terminate()
        proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# basic_auth
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_inspect_basic_auth_mcp_server():
    port = find_free_port()
    username = "agent"
    password = "pass123"
    url = f"http://127.0.0.1:{port}/mcp"
    proc = _start_server(
        SERVERS_DIR / "basic_auth" / "main.py",
        {"MCP_PORT": str(port), "MCP_USERNAME": username, "MCP_PASSWORD": password},
    )
    try:
        basic_creds = base64.b64encode(f"{username}:{password}".encode()).decode()
        wait_for_mcp(url, headers={"authorization": f"Basic {basic_creds}"})

        os.environ["TEST_MCP_PASSWORD"] = password
        config = MCPConfig(
            enabled=True,
            upstream_url=url,
            auth=AuthConfig(
                type="basic",
                username=username,
                password_env="TEST_MCP_PASSWORD",
            ),
        )
        registry = asyncio.run(inspect_mcp_server(config))
        assert len(registry.tools) == 4, f"Expected 4 tools, got {len(registry.tools)}"
    finally:
        os.environ.pop("TEST_MCP_PASSWORD", None)
        proc.terminate()
        proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# oauth2
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_inspect_oauth2_mcp_server():
    port = find_free_port()
    client_id = "test-id"
    client_secret = "test-secret"
    url = f"http://127.0.0.1:{port}/mcp"
    token_url = f"http://127.0.0.1:{port}/oauth/token"
    proc = _start_server(
        SERVERS_DIR / "oauth2" / "main.py",
        {
            "MCP_PORT": str(port),
            "MCP_CLIENT_ID": client_id,
            "MCP_CLIENT_SECRET": client_secret,
        },
    )
    try:
        # Wait for the server to start by polling the token endpoint
        start = time.time()
        while time.time() - start < 10.0:
            try:
                r = httpx.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                    timeout=2.0,
                )
                if r.status_code < 500:
                    break
            except Exception:
                pass
            time.sleep(0.2)
        else:
            raise RuntimeError(f"OAuth2 server not ready: {token_url}")

        os.environ["TEST_MCP_CLIENT_SECRET"] = client_secret
        config = MCPConfig(
            enabled=True,
            upstream_url=url,
            auth=AuthConfig(
                type="oauth2_client_credentials",
                token_url=token_url,
                client_id=client_id,
                client_secret_env="TEST_MCP_CLIENT_SECRET",
            ),
        )
        registry = asyncio.run(inspect_mcp_server(config))
        assert len(registry.tools) == 4, f"Expected 4 tools, got {len(registry.tools)}"
    finally:
        os.environ.pop("TEST_MCP_CLIENT_SECRET", None)
        proc.terminate()
        proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# bearer_auth — wrong token
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_inspect_bearer_auth_rejects_wrong_token():
    port = find_free_port()
    correct_token = "test-token-123"
    wrong_token = "wrong-token-999"
    url = f"http://127.0.0.1:{port}/mcp"
    proc = _start_server(
        SERVERS_DIR / "bearer_auth" / "main.py",
        {"MCP_PORT": str(port), "MCP_BEARER_TOKEN": correct_token},
    )
    try:
        wait_for_mcp(url, headers={"authorization": f"Bearer {correct_token}"})
        config = MCPConfig(
            enabled=True,
            upstream_url=url,
            auth=AuthConfig(type="bearer", token=wrong_token),
        )
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(inspect_mcp_server(config))
    finally:
        proc.terminate()
        proc.wait(timeout=5)
