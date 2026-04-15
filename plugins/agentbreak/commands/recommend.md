---
description: Recommend the highest-value AgentBreak scenarios from the current project and recent changes
allowed-tools: Read, Glob, Grep, Bash
---

# AgentBreak -- Recommend

Run:

```bash
agentbreak recommend
```

This returns a JSON recommendation with:
- blast radius
- recommended presets
- recommended scenarios
- rationale

Use it before editing `scenarios.yaml` by hand.
