# Claude Code Plugin

AgentBreak works as a plugin for Claude Code, giving Claude structured commands to run chaos tests. It handles `.env` backup/restore, proxy lifecycle, and produces actionable resilience reports.

## Install

1. Install the package:

```bash
pip install agentbreak
```

2. Add the plugin in Claude Code:

```
/plugin marketplace add mnvsk97/agentbreak
/plugin install agentbreak@mnvsk97-agentbreak
/reload-plugins
```

You should see three commands when you type `/agentbreak`:

| Command | What it does |
|---------|-------------|
| `/agentbreak:init` | Initialize AgentBreak, analyze your agent codebase |
| `/agentbreak:create-tests` | Generate project-specific chaos scenarios |
| `/agentbreak:run-tests` | Run tests and produce a resilience report |

## Update

To update after a new release, run the same install commands:

```
/plugin marketplace add mnvsk97/agentbreak
/plugin install agentbreak@mnvsk97-agentbreak
/reload-plugins
```

The marketplace `add` fetches the latest from GitHub, and `install` updates the cached version.

!!! tip "If update doesn't take effect"
    Claude Code caches plugins by version. If the plugin version wasn't bumped, the cache won't refresh. Try uninstalling first, then reinstalling:
    ```
    /plugin uninstall agentbreak@mnvsk97-agentbreak
    /plugin marketplace add mnvsk97/agentbreak
    /plugin install agentbreak@mnvsk97-agentbreak
    /reload-plugins
    ```

## Uninstall

```
/plugin uninstall agentbreak@mnvsk97-agentbreak
/reload-plugins
```

## Commands

### `/agentbreak:init`

Full setup flow:

1. Checks AgentBreak is installed (detects uv, venv, suggests right pip command)
2. Runs `agentbreak init` to create `.agentbreak/`
3. Analyzes your codebase (provider, framework, MCP tools, error handling)
4. Asks: **mock or proxy mode?**
    - **Mock** — no API keys needed, synthetic responses
    - **Proxy** — real API traffic, requires valid keys
5. Writes `application.yaml` and `scenarios.yaml` (with standard preset)
6. Validates config (+ `--test-connection` if proxy mode)
7. If MCP enabled, runs `agentbreak inspect` (stops and asks if it fails)
8. Offers to generate project-specific scenarios

### `/agentbreak:create-tests`

Generates project-specific scenarios on top of the standard preset. Analyzes your codebase to find specific MCP tools, models, and integrations, then writes targeted fault scenarios. Can be run anytime to add more scenarios.

### `/agentbreak:run-tests`

Step-by-step test execution:

1. Validate config
2. Inspect MCP (if enabled — stops and asks on failure, never silently skips)
3. Start the chaos proxy
4. **Mock mode:** Quick smoke test — sends curl requests directly to the proxy
5. **Proxy mode:** Wires your agent through the proxy, sends real traffic
6. Collect scorecard and produce a Chaos Test Report

The report includes:

- Traffic summary table
- Per-scenario results (PASS/FAIL with evidence)
- Scoring formula breakdown
- Suggested code-level fixes
- Testing caveat (raw curl vs through-agent)
- Run comparison (if history enabled)

## Safety

- **`.env` is always restored.** The plugin backs up your `.env` before wiring and restores it when done.
- **Proxy is always stopped.** Cleanup runs even if something goes wrong mid-test.
- If something goes wrong, you can always restore manually:

```bash
cp .env.agentbreak-backup .env
pkill -f "agentbreak serve"
```

## Plugin vs CLI

| | CLI | Plugin |
|---|-----|--------|
| Install | `pip install agentbreak` | `pip install agentbreak` + `/plugin install` in Claude Code |
| Usage | Manual commands | Claude runs commands automatically |
| .env handling | Manual backup/restore | Automatic backup + restore on stop |
| Scorecard | `curl` output | Structured report in Claude's context |
| Best for | CI, scripts, manual testing | Interactive development with Claude |

## Plugin versioning

The plugin version is in `plugins/agentbreak/.claude-plugin/plugin.json`. Claude Code caches plugins by this version — bumping it ensures users get fresh files on reinstall.

Current version: **0.4.4**
