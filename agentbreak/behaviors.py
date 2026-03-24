from __future__ import annotations

import json
from typing import Callable


def empty(body: bytes) -> bytes:
    return b""


def invalid_json(body: bytes) -> bytes:
    return b"{not valid"


def malformed_tool_calls(body: bytes) -> bytes:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return b"{not valid"

    if not isinstance(payload, dict):
        return b"{not valid"

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict):
                message["tool_calls"] = "INVALID"
                return json.dumps(payload).encode("utf-8")

    payload["tool_calls"] = "INVALID"
    return json.dumps(payload).encode("utf-8")


RESPONSE_BEHAVIORS: dict[str, Callable[[bytes], bytes]] = {
    "empty": empty,
    "invalid_json": invalid_json,
    "malformed_tool_calls": malformed_tool_calls,
}


def apply_response_behavior(body: bytes, name: str) -> bytes:
    fn = RESPONSE_BEHAVIORS.get(name)
    if fn is None:
        return body
    try:
        return fn(body)
    except Exception:
        return body
