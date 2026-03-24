# DeepAgents-Style ReAct Agent

Lightweight ReAct agent using the `openai` Python SDK directly. No framework — just a tool-calling loop with retry logic.

## Setup

```bash
cd examples/agents/deepagents
pip install -r requirements.txt
cp .env.example .env
python agent.py
```

## Chaos testing

Point at AgentBreak and use the bundled scenarios:

```bash
agentbreak serve --scenarios examples/agents/deepagents/scenarios.yaml
OPENAI_BASE_URL=http://localhost:5005/v1 python agent.py
```

See `.env.example` for all configuration variables.
