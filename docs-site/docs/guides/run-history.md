# Run History

Track your agent's resilience over time by comparing runs.

## Enable history

```yaml
# .agentbreak/application.yaml
history:
  enabled: true
```

## Label your runs

```bash
agentbreak serve --label "baseline - no retries"
```

Run your agent, stop the proxy, then start a new run:

```bash
agentbreak serve --label "added retry logic"
```

## View past runs

```bash
agentbreak history
```

## Compare runs

```bash
agentbreak history compare 1 2
```

This shows a side-by-side diff of two runs — scores, fault counts, and outcomes — so you can see if your changes improved resilience.

## Show run details

```bash
agentbreak history show 1
```
