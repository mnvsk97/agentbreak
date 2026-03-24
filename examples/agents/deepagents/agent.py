"""DeepAgents-style ReAct agent using the OpenAI SDK directly.

A lightweight tool-calling loop that works with any OpenAI-compatible
endpoint.  Point OPENAI_BASE_URL at AgentBreak to chaos-test the agent.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:5005/v1")
API_KEY = os.getenv("OPENAI_API_KEY", "test-key")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", "2.0"))

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# ---------------------------------------------------------------------------
# Local tool implementations (standalone mode — no MCP server required)
# ---------------------------------------------------------------------------

TOOL_IMPLEMENTATIONS: dict[str, Any] = {}


def _register(fn):
    TOOL_IMPLEMENTATIONS[fn.__name__] = fn
    return fn


@_register
def list_report_sections(report_type: str) -> str:
    sections = {
        "quarterly": ["Executive Summary", "Revenue", "Churn", "Pipeline", "Actions"],
        "monthly": ["Summary", "KPIs", "Highlights", "Risks"],
    }
    return json.dumps(sections.get(report_type, ["Overview", "Details"]))


@_register
def fetch_kpi_snapshot(metric_names: list[str], as_of: str) -> str:
    data = {m: {"value": round(100 + hash(m + as_of) % 500, 2), "unit": "USD"} for m in metric_names}
    return json.dumps(data)


@_register
def lookup_account_notes(account_id: str) -> str:
    return json.dumps([
        {"date": "2026-03-20", "note": f"Account {account_id}: renewal discussion positive."},
        {"date": "2026-03-15", "note": f"Account {account_id}: upsell opportunity identified."},
    ])


@_register
def render_report_brief(account_id: str, report_type: str) -> str:
    return json.dumps({"account": account_id, "type": report_type, "brief": "All KPIs trending up. Pipeline healthy."})

# ---------------------------------------------------------------------------
# OpenAI tool schemas
# ---------------------------------------------------------------------------

TOOLS_SCHEMA = [
    {"type": "function", "function": {"name": "list_report_sections", "description": "List canonical sections for a report type.", "parameters": {"type": "object", "properties": {"report_type": {"type": "string"}}, "required": ["report_type"]}}},
    {"type": "function", "function": {"name": "fetch_kpi_snapshot", "description": "Fetch KPI data for metrics and date.", "parameters": {"type": "object", "properties": {"metric_names": {"type": "array", "items": {"type": "string"}}, "as_of": {"type": "string"}}, "required": ["metric_names", "as_of"]}}},
    {"type": "function", "function": {"name": "lookup_account_notes", "description": "Look up recent notes for an account.", "parameters": {"type": "object", "properties": {"account_id": {"type": "string"}}, "required": ["account_id"]}}},
    {"type": "function", "function": {"name": "render_report_brief", "description": "Generate a compact report brief.", "parameters": {"type": "object", "properties": {"account_id": {"type": "string"}, "report_type": {"type": "string"}}, "required": ["account_id", "report_type"]}}},
]

# ---------------------------------------------------------------------------
# ReAct loop with retry logic
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a concise revenue operations assistant. "
    "Use the available tools to assemble report evidence before answering. "
    "When you have enough evidence, produce a compact report."
)


def _call_llm(messages: list[dict], retry: int = 0) -> Any:
    """Call the chat completions endpoint with exponential back-off."""
    try:
        return client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            temperature=0,
        )
    except (RateLimitError, APITimeoutError, APIError) as exc:
        if retry >= MAX_RETRIES:
            raise
        wait = RETRY_BACKOFF ** (retry + 1)
        print(f"  [retry {retry + 1}/{MAX_RETRIES}] {type(exc).__name__}: {exc} — waiting {wait:.1f}s")
        time.sleep(wait)
        return _call_llm(messages, retry + 1)


def _execute_tool(name: str, arguments: dict) -> str:
    fn = TOOL_IMPLEMENTATIONS.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        return fn(**arguments)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def run(user_query: str, max_turns: int = 10) -> str:
    """Execute a full ReAct loop and return the final text answer."""
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    for turn in range(max_turns):
        print(f"\n--- Turn {turn + 1} ---")
        response = _call_llm(messages)
        choice = response.choices[0]

        if choice.finish_reason == "stop" or not choice.message.tool_calls:
            answer = choice.message.content or ""
            print(f"Assistant: {answer[:200]}{'...' if len(answer) > 200 else ''}")
            return answer

        # Process tool calls
        messages.append(choice.message.model_dump())
        for tc in choice.message.tool_calls:
            args = json.loads(tc.function.arguments)
            print(f"  Tool call: {tc.function.name}({json.dumps(args, separators=(',', ':'))})")
            result = _execute_tool(tc.function.name, args)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return "Max turns reached without a final answer."


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    query = "Generate a quarterly report brief for account ACC-1234, including KPI highlights for revenue and churn as of 2026-03-24."
    print(f"Query: {query}\n")
    answer = run(query)
    print(f"\n=== Final Answer ===\n{answer}")
