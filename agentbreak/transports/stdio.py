"""Stdio subprocess transport for MCP."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from agentbreak.mcp_protocol import MCPRequest
from agentbreak.transports.base import DEFAULT_TRANSPORT_TIMEOUT, MCPTransport


class StdioTransport(MCPTransport):
    """Transport that communicates with an MCP server via a stdio subprocess.

    The subprocess is started on first use and restarted automatically if it
    terminates unexpectedly (one restart attempt per request).  All requests are
    serialised through an asyncio.Lock because stdio is a single-channel pipe.
    """

    def __init__(
        self,
        command: tuple[str, ...],
        timeout: float = DEFAULT_TRANSPORT_TIMEOUT,
    ) -> None:
        if not command:
            raise ValueError("upstream_command must not be empty for stdio transport")
        self.command = command
        self.timeout = timeout
        self._process: asyncio.subprocess.Process | None = None
        self._lock: asyncio.Lock | None = None
        self._started = False

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def _ensure_process(self) -> asyncio.subprocess.Process:
        if self._process is None or self._process.returncode is not None:
            try:
                self._process = await asyncio.create_subprocess_exec(
                    *self.command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            except (FileNotFoundError, PermissionError, OSError) as exc:
                raise RuntimeError(
                    f"Failed to start stdio subprocess: {exc}"
                ) from exc
        return self._process

    async def start(self) -> None:
        """Pre-start the subprocess (optional; happens lazily on first request)."""
        if not self._started:
            self._started = True
            await self._ensure_process()

    async def send_request(self, request: MCPRequest) -> dict[str, Any]:
        async with self._get_lock():
            for attempt in range(2):
                process = await self._ensure_process()
                assert process.stdin is not None and process.stdout is not None
                line = request.to_json_bytes().decode("utf-8") + "\n"
                try:
                    process.stdin.write(line.encode())
                    await process.stdin.drain()
                except (BrokenPipeError, ConnectionResetError):
                    self._process = None
                    if attempt == 0:
                        continue
                    raise RuntimeError(
                        "Stdio upstream closed the connection unexpectedly"
                    )
                try:
                    response_line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=self.timeout,
                    )
                except asyncio.TimeoutError as exc:
                    raise TimeoutError(
                        f"Stdio upstream timed out after {self.timeout}s"
                    ) from exc
                if not response_line:
                    self._process = None
                    if attempt == 0:
                        continue
                    raise RuntimeError(
                        "Stdio upstream closed the connection unexpectedly"
                    )
                try:
                    return json.loads(response_line.decode().strip())
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"Stdio upstream returned malformed JSON: {exc}"
                    ) from exc
            raise RuntimeError("Stdio upstream failed after restart attempt")

    async def stop(self) -> None:
        """Terminate the subprocess and clean up."""
        if self._process is not None:
            try:
                if self._process.stdin:
                    self._process.stdin.close()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except Exception:
                self._process.kill()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=2.0)
                except Exception:
                    pass
            self._process = None
        self._started = False
