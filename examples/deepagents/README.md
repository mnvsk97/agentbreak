# DeepAgents-Style ReAct Agent

A lightweight ReAct agent built directly on the `openai` Python SDK. No framework
beyond the SDK itself -- just a tool-calling loop that works with any
OpenAI-compatible endpoint.

## What this example does

The agent receives a natural-language query, calls reporting tools
(list sections, fetch KPIs, look up account notes, render a brief), and
synthesises the results into a compact report. Tools are implemented locally
so the example runs standalone without an MCP server.

## Setup

```bash
cd examples/deepagents
pip install -r requirements.txt
cp .env.example .env   # edit as needed
```

## Running standalone (no AgentBreak)

Point `OPENAI_BASE_URL` at any OpenAI-compatible endpoint:

```bash
export OPENAI_BASE_URL=https://api.openai.com/v1
export OPENAI_API_KEY=sk-...
python agent.py
```

## Chaos testing with AgentBreak

1. Start AgentBreak with the bundled scenarios:

   ```bash
   agentbreak serve \
     --config application.yaml \
     --scenarios examples/deepagents/scenarios.yaml
   ```

2. Point the agent at AgentBreak:

   ```bash
   export OPENAI_BASE_URL=http://localhost:5005/v1
   python agent.py
   ```

AgentBreak will randomly inject faults (429 rate limits, latency spikes, 503
tool errors) according to `scenarios.yaml`. The agent's retry logic handles
transient errors -- watch the `[retry ...]` log lines to see resilience in
action.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_BASE_URL` | `http://localhost:5005/v1` | LLM endpoint (set to AgentBreak for chaos testing) |
| `OPENAI_API_KEY` | `test-key` | API key passed to the endpoint |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model name |
| `MAX_RETRIES` | `3` | Retries on rate-limit / timeout / API errors |
| `RETRY_BACKOFF` | `2.0` | Exponential back-off base (seconds) |
