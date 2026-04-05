---
name: agentbreak
description: >
  Chaos-test any LLM agent using AgentBreak. Analyzes the codebase,
  generates chaos scenarios, starts the proxy, wires the agent, and interprets results.
  TRIGGER when: user wants to test agent resilience, reliability, robustness, or fault tolerance.
  Also trigger for: chaos testing, stress testing, failure testing, error injection, fault injection,
  "what happens when my API fails", "how does my agent handle errors", "break my agent",
  "test my agent", simulate outages, inject latency, test retries, test timeouts,
  or any request about making an LLM agent more resilient to failures.
  DO NOT TRIGGER when: unit testing, load/performance benchmarking, or security/penetration testing.
---

# AgentBreak — Chaos Test Your Agent

Three commands:

1. `/agentbreak:init` — install, analyze codebase, configure `.agentbreak/`
2. `/agentbreak:create-tests` — generate project-specific chaos scenarios
3. `/agentbreak:run-tests` — validate, serve proxy, send traffic, produce report

If the plugin isn't installed yet:

```
/plugin marketplace add mnvsk97/agentbreak
/plugin install agentbreak@mnvsk97-agentbreak
/reload-plugins
```

Start with `/agentbreak:init`.
