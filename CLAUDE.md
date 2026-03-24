# Claude Code — AgentBreak

## What this repo is

A Python package that proxies LLM (OpenAI + Anthropic) and MCP traffic, injecting configurable faults. Config lives in `.agentbreak/`, created by `agentbreak init`.

## Quick commands

```bash
pip install -e '.[dev]'
agentbreak init
agentbreak validate
agentbreak serve
```

For MCP: `agentbreak inspect` then `serve`.

## Skill

Install via `npx skills add mnvsk97/agentbreak`, then use `/agentbreak`.

## Verification

Before suggesting a change is done: run **`agentbreak verify`**.
