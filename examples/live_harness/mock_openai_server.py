from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


HOST = os.getenv("MOCK_OPENAI_HOST", "127.0.0.1")
PORT = int(os.getenv("MOCK_OPENAI_PORT", "5010"))

app = FastAPI(title="agentbreak-mock-openai")


def _extract_account_id(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        content = message.get("content")
        if isinstance(content, str):
            match = re.search(r"(acct-[a-z0-9_-]+)", content.lower())
            if match:
                return match.group(1)
    return "acct-acme"


def _text_from_tool_messages(messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for message in messages:
        if message.get("role") == "tool":
            content = message.get("content", "")
            if isinstance(content, str):
                parts.append(content)
            else:
                parts.append(json.dumps(content, sort_keys=True))
    return "\n".join(parts)


def _tool_response(tool_calls: list[dict[str, Any]], model: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-mock-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": tool_calls,
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _final_response(text: str, model: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-mock-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> JSONResponse:
    payload = await request.json()
    messages = payload.get("messages", [])
    model = payload.get("model", "gpt-4o-mini")
    tool_names = [tool["function"]["name"] for tool in payload.get("tools", []) if tool.get("type") == "function"]
    account_id = _extract_account_id(messages)

    print(
        f"[mock-openai] request model={model} tools={tool_names} message_count={len(messages)} account_id={account_id}",
        flush=True,
    )

    if any(message.get("role") == "tool" for message in messages):
        evidence = _text_from_tool_messages(messages)
        response_text = (
            f"Report for {account_id}: sections and evidence gathered successfully. "
            f"KPI and note summary follow.\n\nEvidence:\n{evidence}"
        )
        return JSONResponse(_final_response(response_text, model))

    tool_calls = [
        {
            "id": "call_sections",
            "type": "function",
            "function": {
                "name": "list_report_sections",
                "arguments": json.dumps({"report_type": "quarterly_business_review"}),
            },
        },
        {
            "id": "call_kpis",
            "type": "function",
            "function": {
                "name": "fetch_kpi_snapshot",
                "arguments": json.dumps(
                    {
                        "metric_names": ["arr", "active_users", "nrr", "ticket_backlog"],
                        "as_of": "2026-03-18",
                    }
                ),
            },
        },
        {
            "id": "call_notes",
            "type": "function",
            "function": {
                "name": "lookup_account_notes",
                "arguments": json.dumps({"account_id": account_id}),
            },
        },
        {
            "id": "call_brief",
            "type": "function",
            "function": {
                "name": "render_report_brief",
                "arguments": json.dumps({"account_id": account_id, "report_type": "quarterly_business_review"}),
            },
        },
    ]
    return JSONResponse(_tool_response(tool_calls, model))


def main() -> None:
    print(f"[mock-openai] starting on http://{HOST}:{PORT}", flush=True)
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
