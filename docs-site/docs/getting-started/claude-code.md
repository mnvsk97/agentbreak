# Claude Code Skill

If you use [Claude Code](https://docs.anthropic.com/en/docs/claude-code), AgentBreak has a guided skill that automates the entire workflow — no manual config needed.

## Prerequisites

The skill uses the AgentBreak plugin for Claude Code. Set it up first — see [Plugin](plugin.md).

## Install

```bash
npx skills add mnvsk97/agentbreak
```

## Usage

Type `/agentbreak` in Claude Code. The skill runs a 6-step workflow:

### Step 1: Setup
Installs AgentBreak and initializes `.agentbreak/` if needed.

### Step 2: Analyze Codebase
Scans your project to detect:

- **LLM provider** — OpenAI or Anthropic
- **Agent framework** — LangGraph, LangChain, CrewAI, raw SDK, etc.
- **MCP tools** — tool names, server URLs
- **Error handling** — retry logic, timeouts, try/except patterns

You review the findings before proceeding.

### Step 3: Generate Config
Creates tailored `application.yaml` and `scenarios.yaml` based on what it found. Scenarios are chosen to target gaps — if your agent has no retry logic, it'll prioritize error scenarios.

You review and adjust the scenarios before proceeding.

### Step 4: Start the Proxy
Runs `agentbreak inspect` (if MCP), validates config, and starts the chaos proxy in the background.

### Step 5: Wire Agent & Send Traffic
Automatically rewires your agent's `.env` to point at AgentBreak, runs your agent, sends traffic through the proxy, then restores the original config.

### Step 6: Results & Action Plan
Reads the scorecard and produces a structured **Chaos Test Report** with:

- Traffic summary and resilience score
- What happened for each fault that fired
- Numbered issues with severity and evidence
- Specific, copy-pasteable code fixes referencing your actual files
- If history is enabled, comparison with previous runs

You can then ask Claude to apply the fixes directly.

## What makes it useful

The skill does what you'd otherwise do manually — but it picks the *right* scenarios for your codebase. An agent with no retry logic gets rate limit errors. An agent with MCP tools gets per-tool fault injection. The report ties failures back to specific lines in your code.

## Presets

If you'd rather skip the analysis and use a preset:

```yaml
preset: brownout
```

The skill also supports presets — just tell Claude which preset you want during Step 3.
