---
description: Summarize what broke in an AgentBreak run and what to fix next
allowed-tools: Read, Bash
---

# AgentBreak -- Synthesize

Run:

```bash
agentbreak synthesize --run-id 1
```

Optional comparison:

```bash
agentbreak synthesize --run-id 2 --compare-run-id 1
```

This returns a compact JSON summary of failure themes, affected surfaces, and next fixes.
