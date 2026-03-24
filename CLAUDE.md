# Claude Code (and similar) — AgentBreak

## What this repo is

A Python package that proxies **LLM chat completions** and **MCP** traffic and injects **configurable faults** from `scenarios.yaml`. Configuration is **`application.yaml`** + **`scenarios.yaml`**, not legacy `agentbreak start` flags.

## Quick commands

```bash
pip install -e '.[dev]'
cp config.example.yaml application.yaml
cp scenarios.example.yaml scenarios.yaml
# Edit application.yaml: llm.mode mock|proxy, mcp.enabled true|false

agentbreak validate --config application.yaml --scenarios scenarios.yaml
agentbreak serve --config application.yaml --scenarios scenarios.yaml
```

For MCP mirroring: `agentbreak inspect --config application.yaml` then `serve`.

## Slash command

Project command definition: **`.claude-plugin/commands/agentbreak.md`** (install via `.claude-plugin/plugin.json`). It should stay in sync with **`README.md`**.

## Skills

Bundled workflows under **`skills/`** (copy each folder into a client skills directory if needed):

| Skill | Path |
|-------|------|
| AgentBreak chaos testing | `skills/agentbreak-testing/SKILL.md` |
| Run / debug tests | `skills/tester/SKILL.md` |
| Author new tests | `skills/test-generator/SKILL.md` |

## Docs map

| File | Purpose |
|------|---------|
| `README.md` | User-facing overview, scenario format, examples |
| `CONTRIBUTING.md` | Dev setup, verify, validate, inspect |
| `AGENTS.md` | Agent/coding guidelines for this repo |
| `docs/README.md` | Index of extra docs |
| `docs/FAILURE_MODES.md` | Scope of simulated failures |
| `docs/TODO_SCENARIOS.md` | Deferred scenario targets |
| `docs/live-testing.md` | `agentbreak verify --live` harness |

## Verification

Before suggesting a change is done: run **`agentbreak verify`**. Use **`agentbreak verify --live`** only when the change touches the live harness or full stack.
