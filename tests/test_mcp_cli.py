"""Tests for agentbreak mcp CLI subcommands: test, list-tools, call-tool."""
from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from agentbreak import mcp_proxy
from agentbreak.main import cli


runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": 1, "result": result}


def _make_error_response(code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": 1, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# agentbreak mcp test
# ---------------------------------------------------------------------------

class TestMcpTest:
    def test_success(self) -> None:
        response = _make_response({
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "serverInfo": {"name": "my-server", "version": "2.0"},
        })
        with patch("agentbreak.mcp_proxy._send_one_request", new=AsyncMock(return_value=response)):
            result = runner.invoke(cli, ["mcp", "test", "--url", "http://localhost:5001"])
        assert result.exit_code == 0
        assert "my-server" in result.output
        assert "2.0" in result.output

    def test_connection_failure(self) -> None:
        with patch(
            "agentbreak.mcp_proxy._send_one_request",
            new=AsyncMock(side_effect=RuntimeError("connection refused")),
        ):
            result = runner.invoke(cli, ["mcp", "test", "--url", "http://localhost:5001"])
        assert result.exit_code == 1

    def test_server_error_response(self) -> None:
        response = _make_error_response(-32603, "Internal error")
        with patch("agentbreak.mcp_proxy._send_one_request", new=AsyncMock(return_value=response)):
            result = runner.invoke(cli, ["mcp", "test", "--url", "http://localhost:5001"])
        assert result.exit_code == 1

    def test_invalid_transport(self) -> None:
        result = runner.invoke(cli, ["mcp", "test", "--transport", "grpc"])
        assert result.exit_code != 0

    def test_stdio_missing_command(self) -> None:
        result = runner.invoke(cli, ["mcp", "test", "--transport", "stdio"])
        assert result.exit_code != 0

    def test_passes_correct_method(self) -> None:
        captured: list[str] = []
        response = _make_response({"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {}})

        async def fake_send(method: str, params: Any, transport: str, url: str, command: tuple, timeout: float) -> dict:
            captured.append(method)
            return response

        with patch("agentbreak.mcp_proxy._send_one_request", new=fake_send):
            result = runner.invoke(cli, ["mcp", "test"])
        assert captured == ["initialize"]


# ---------------------------------------------------------------------------
# agentbreak mcp list-tools
# ---------------------------------------------------------------------------

class TestMcpListTools:
    def test_lists_tools(self) -> None:
        response = _make_response({
            "tools": [
                {"name": "echo", "description": "Echo text."},
                {"name": "get_time", "description": "Get current time."},
            ]
        })
        with patch("agentbreak.mcp_proxy._send_one_request", new=AsyncMock(return_value=response)):
            result = runner.invoke(cli, ["mcp", "list-tools"])
        assert result.exit_code == 0
        assert "echo" in result.output
        assert "Echo text." in result.output
        assert "get_time" in result.output

    def test_no_tools(self) -> None:
        response = _make_response({"tools": []})
        with patch("agentbreak.mcp_proxy._send_one_request", new=AsyncMock(return_value=response)):
            result = runner.invoke(cli, ["mcp", "list-tools"])
        assert result.exit_code == 0
        assert "No tools available" in result.output

    def test_server_error(self) -> None:
        response = _make_error_response(-32601, "Method not found")
        with patch("agentbreak.mcp_proxy._send_one_request", new=AsyncMock(return_value=response)):
            result = runner.invoke(cli, ["mcp", "list-tools"])
        assert result.exit_code == 1

    def test_connection_failure(self) -> None:
        with patch(
            "agentbreak.mcp_proxy._send_one_request",
            new=AsyncMock(side_effect=TimeoutError("timed out")),
        ):
            result = runner.invoke(cli, ["mcp", "list-tools"])
        assert result.exit_code == 1

    def test_passes_correct_method(self) -> None:
        captured: list[str] = []
        response = _make_response({"tools": []})

        async def fake_send(method: str, params: Any, transport: str, url: str, command: tuple, timeout: float) -> dict:
            captured.append(method)
            return response

        with patch("agentbreak.mcp_proxy._send_one_request", new=fake_send):
            runner.invoke(cli, ["mcp", "list-tools"])
        assert captured == ["tools/list"]


# ---------------------------------------------------------------------------
# agentbreak mcp call-tool
# ---------------------------------------------------------------------------

class TestMcpCallTool:
    def test_prints_text_content(self) -> None:
        response = _make_response({
            "content": [{"type": "text", "text": "Hello from echo!"}],
            "isError": False,
        })
        with patch("agentbreak.mcp_proxy._send_one_request", new=AsyncMock(return_value=response)):
            result = runner.invoke(cli, ["mcp", "call-tool", "echo", "--args", '{"text": "hello"}'])
        assert result.exit_code == 0
        assert "Hello from echo!" in result.output

    def test_non_text_content_printed_as_json(self) -> None:
        response = _make_response({
            "content": [{"type": "image", "url": "http://example.com/img.png"}],
        })
        with patch("agentbreak.mcp_proxy._send_one_request", new=AsyncMock(return_value=response)):
            result = runner.invoke(cli, ["mcp", "call-tool", "snapshot"])
        assert result.exit_code == 0
        assert "image" in result.output

    def test_empty_content_prints_result(self) -> None:
        response = _make_response({"status": "ok"})
        with patch("agentbreak.mcp_proxy._send_one_request", new=AsyncMock(return_value=response)):
            result = runner.invoke(cli, ["mcp", "call-tool", "ping"])
        assert result.exit_code == 0
        assert "ok" in result.output

    def test_invalid_args_json(self) -> None:
        result = runner.invoke(cli, ["mcp", "call-tool", "echo", "--args", "not-json"])
        assert result.exit_code != 0

    def test_args_not_object(self) -> None:
        result = runner.invoke(cli, ["mcp", "call-tool", "echo", "--args", '"string"'])
        assert result.exit_code != 0

    def test_server_error(self) -> None:
        response = _make_error_response(-32000, "Tool execution failed")
        with patch("agentbreak.mcp_proxy._send_one_request", new=AsyncMock(return_value=response)):
            result = runner.invoke(cli, ["mcp", "call-tool", "broken_tool"])
        assert result.exit_code == 1

    def test_passes_correct_params(self) -> None:
        captured: list[dict] = []
        response = _make_response({"content": [{"type": "text", "text": "ok"}]})

        async def fake_send(method: str, params: Any, transport: str, url: str, command: tuple, timeout: float) -> dict:
            captured.append({"method": method, "params": params})
            return response

        with patch("agentbreak.mcp_proxy._send_one_request", new=fake_send):
            runner.invoke(cli, ["mcp", "call-tool", "echo", "--args", '{"text": "hi"}'])
        assert captured[0]["method"] == "tools/call"
        assert captured[0]["params"]["name"] == "echo"
        assert captured[0]["params"]["arguments"] == {"text": "hi"}

    def test_invalid_transport(self) -> None:
        result = runner.invoke(cli, ["mcp", "call-tool", "echo", "--transport", "grpc"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# agentbreak mcp start (basic validation tests - not running the server)
# ---------------------------------------------------------------------------

class TestMcpStart:
    def test_help_is_available(self) -> None:
        result = runner.invoke(cli, ["mcp", "start", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output.lower() or "mode" in result.output.lower()

    def test_invalid_mode(self) -> None:
        result = runner.invoke(cli, ["mcp", "start", "--mode", "invalid"])
        assert result.exit_code != 0

    def test_proxy_mode_requires_url_for_http(self) -> None:
        result = runner.invoke(cli, [
            "mcp", "start",
            "--mode", "proxy",
            "--upstream-transport", "http",
        ])
        assert result.exit_code != 0

    def test_proxy_mode_requires_command_for_stdio(self) -> None:
        result = runner.invoke(cli, [
            "mcp", "start",
            "--mode", "proxy",
            "--upstream-transport", "stdio",
        ])
        assert result.exit_code != 0
