# AgentBreak 0.3.0 Migration Guide

## Overview

AgentBreak 0.3.0 introduces a major refactor with a new modular package structure and a unified multi-service config format. This guide covers everything needed to upgrade from 0.2.x.

## What Changed

### Package Structure

The internal module layout changed from monolithic files to a modular structure:

Old (0.2.x):
- `agentbreak/main.py` - LLM proxy + CLI (~500 lines)
- `agentbreak/mcp_proxy.py` - MCP proxy + CLI (~800 lines)
- `agentbreak/mcp_protocol.py` - Protocol dataclasses
- `agentbreak/mcp_transport.py` - Transport abstraction

New (0.3.0):
- `agentbreak/config/` - Config models and loader (Pydantic)
- `agentbreak/core/` - Shared proxy, fault injection, latency, statistics
- `agentbreak/protocols/` - MCP and other protocol definitions
- `agentbreak/services/` - OpenAI and MCP service implementations
- `agentbreak/transports/` - HTTP, SSE, and stdio transports
- `agentbreak/utils/` - Shared utilities
- `agentbreak/api/` - Health and metrics endpoints
- `agentbreak/runner.py` - MultiServiceRunner for running multiple proxies

### Config File Format

A new unified config format (version 1.0) allows running multiple services from a single file.

**Old format (0.2.x single-service):**

```yaml
mode: proxy
upstream_url: https://api.openai.com
scenario: mixed-transient
fail_rate: 0.2
```

**New format (0.3.0 multi-service):**

```yaml
version: "1.0"
services:
  - name: llm-proxy
    type: openai
    mode: proxy
    port: 5000
    upstream_url: https://api.openai.com
    scenario: mixed-transient
    fault:
      overall_rate: 0.2
      available_codes: [429, 500, 503]
      latency_probability: 0.1
      latency_ms_min: 100
      latency_ms_max: 2000
```

The old config format continues to work via the existing CLI flags. The new format is opt-in via `--config-file`.

### API Endpoint Changes

Metrics endpoints are now service-prefixed to support multi-service deployments:

Old:
- `GET /_agentbreak/scorecard`
- `GET /_agentbreak/stats`

New:
- `GET /_agentbreak/{service_name}/scorecard`
- `GET /_agentbreak/{service_name}/stats`
- `GET /health` (new - available across all services)

## Upgrade Steps

### Step 1: Install 0.3.0

```bash
pip install --upgrade agentbreak==0.3.0
```

### Step 2: CLI Usage (No Changes Required)

All existing CLI commands continue to work:

```bash
# These still work exactly as before
agentbreak start --mode proxy --upstream-url https://api.openai.com --fail-rate 0.2
agentbreak mcp start --mode mock --scenario mcp-mixed-transient
```

### Step 3: Migrate Config Files (Optional)

If you use a YAML config file, migrate to the new format for multi-service support.

Convert old config:
```yaml
mode: proxy
upstream_url: https://api.openai.com
fail_rate: 0.2
```

To new format:
```yaml
version: "1.0"
services:
  - name: default
    type: openai
    mode: proxy
    port: 5000
    upstream_url: https://api.openai.com
    fault:
      overall_rate: 0.2
```

Then use:
```bash
agentbreak run --config-file my-config.yaml
```

### Step 4: Update Metrics Endpoint URLs

If you query metrics endpoints, update the URLs:

Old: `http://localhost:5000/_agentbreak/scorecard`
New: `http://localhost:5000/_agentbreak/default/scorecard`

### Step 5: Update Direct Imports (If Applicable)

If your code imports agentbreak internals directly, update the import paths:

Old:
```python
from agentbreak.mcp_protocol import MCPRequest, MCPResponse
from agentbreak.mcp_transport import MCPTransport
```

New:
```python
from agentbreak.protocols.mcp import MCPRequest, MCPResponse
from agentbreak.transports.base import MCPTransport
```

## Multi-Service Example

One of the major new features is running LLM and MCP proxies simultaneously:

```yaml
version: "1.0"
services:
  - name: llm
    type: openai
    mode: proxy
    port: 5000
    upstream_url: https://api.openai.com
    fault:
      overall_rate: 0.1

  - name: mcp-tools
    type: mcp
    mode: proxy
    port: 5001
    upstream_url: http://localhost:3000
    upstream_transport: http
    fault:
      overall_rate: 0.3
      available_codes: [-32603, -32001]
```

```bash
agentbreak run --config-file multi-service.yaml
```

This starts both proxies in separate threads, each on their own port.

## Using Scenarios

The new scenario system makes it easy to apply pre-built fault patterns:

```bash
# List available scenarios
agentbreak list-scenarios

# Apply a scenario via config
```

```yaml
version: "1.0"
services:
  - name: llm
    type: openai
    mode: proxy
    port: 5000
    upstream_url: https://api.openai.com
    scenario: rate-limit-storm
```

See `examples/` for complete scenario config examples.

## Troubleshooting

### ImportError on agentbreak internals

If you get `ImportError: cannot import name 'X' from 'agentbreak.mcp_proxy'`, the module was reorganized. Check the new module locations above or use `from agentbreak.protocols.mcp import ...` and `from agentbreak.transports.base import ...`.

### Metrics 404 errors

If `/_agentbreak/scorecard` returns 404, update to `/_agentbreak/{service_name}/scorecard` where `service_name` defaults to `default` for single-service setups.

### Config file not recognized

Ensure your config file has `version: "1.0"` at the top. Files without a version header are treated as the old flat format.

## Support

Report issues at https://github.com/mnvsk97/agentbreak/issues
