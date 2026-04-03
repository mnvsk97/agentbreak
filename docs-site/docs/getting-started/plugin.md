# Claude Code Plugin

AgentBreak works as an MCP plugin for Claude Code, giving Claude structured tools instead of shell commands. This means safer .env handling, automatic cleanup, and Claude can run chaos tests autonomously.

## Install

```bash
pip install agentbreak[plugin]
```

## Configure

Add to your Claude Code settings (`.claude/settings.json` or project settings):

```json
{
  "mcpServers": {
    "agentbreak": {
      "command": "agentbreak",
      "args": ["mcp-server"]
    }
  }
}
```

## Usage

Once configured, Claude has access to these tools:

| Tool | What it does |
|------|-------------|
| `agentbreak_init` | Create `.agentbreak/` config directory |
| `agentbreak_analyze` | Scan codebase for provider, framework, MCP tools, error handling |
| `agentbreak_generate_config` | Generate tailored scenarios based on analysis |
| `agentbreak_inspect` | Discover MCP tools from upstream server |
| `agentbreak_validate` | Check config files for errors |
| `agentbreak_start` | Start the chaos proxy |
| `agentbreak_wire` | Backup .env and rewire agent to proxy |
| `agentbreak_revert` | Restore original .env from backup |
| `agentbreak_stop` | Stop proxy + auto-revert .env |
| `agentbreak_scorecard` | Fetch scorecard from running proxy |
| `agentbreak_status` | Check proxy and wiring state |

### With the skill

The plugin pairs with the `/agentbreak` skill for a guided workflow:

```bash
npx skills add mnvsk97/agentbreak
```

Type `/agentbreak` and Claude walks you through the full chaos testing flow using the MCP tools.

### Without the skill

You can also just ask Claude directly:

> "Run chaos tests on my agent"

Claude will use the AgentBreak tools to analyze your codebase, generate scenarios, start the proxy, wire your agent, and report results.

## Safety guarantees

The plugin manages state in code, not in prompts:

- **`agentbreak_stop` auto-reverts your .env** — your app config is never left pointing at a dead proxy, even if Claude crashes or the conversation ends.
- **`agentbreak_revert`** can be called at any time as a safety valve.
- **`agentbreak_status`** lets Claude (or you) check what's running and what's wired at any point.

If something goes wrong, you can always run from the CLI:

```bash
# Check if a backup exists
ls .env.agentbreak-backup

# Restore manually
cp .env.agentbreak-backup .env
```

## Plugin vs CLI

| | CLI | Plugin |
|---|-----|--------|
| Install | `pip install agentbreak` | `pip install agentbreak[plugin]` |
| Usage | Manual commands | Claude calls tools automatically |
| .env handling | Manual backup/restore | Automatic backup + auto-revert on stop |
| Scorecard | `curl` output | Structured JSON in Claude's context |
| Best for | CI, scripts, manual testing | Interactive development with Claude |
