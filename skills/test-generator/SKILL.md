---
name: test-generator
description: Add or extend pytest tests for AgentBreak -- TestClient, CliRunner, tmp_path YAML fixtures, DummyAsyncClient for upstream LLM, deterministic unit tests.
---

# Test Generator

Use this skill to add tests, increase coverage, or lock in behavior for AgentBreak.

## Principles

- Match existing tests in `tests/test_main.py` and `tests/test_behaviors.py` for naming, layout, and assertion style.
- Stay deterministic. No live network in unit tests. Use fakes and temp files.
- Respect `conftest.py`. The autouse fixture resets `main.service_state` and `DummyAsyncClient`. Do not rely on cross-test leakage.
- One behavior per test unless the user explicitly wants an E2E-style test.

## Patterns

### Config on disk (tmp_path)

Build `application.yaml` and `scenarios.yaml` under `tmp_path`, then call loaders or `main.load_service_state`. Use `yaml.safe_dump` with plain dicts matching `config.example.yaml` / `scenarios.example.yaml` shapes.

### FastAPI

```python
from fastapi.testclient import TestClient
from agentbreak import main

client = TestClient(main.app)
# Set main.service_state before the request (see existing tests).
```

### CLI

```python
from typer.testing import CliRunner
from agentbreak import main

runner = CliRunner()
result = runner.invoke(main.cli, ["validate", "--config", str(cfg)])
assert result.exit_code == 0
```

### Upstream LLM (httpx)

For proxy LLM paths, configure `tests.helpers.DummyAsyncClient`:

- `DummyAsyncClient.responses` -- queue of `DummyResponse` instances
- `DummyAsyncClient.error` -- raise on post
- `DummyAsyncClient.calls` -- inspect URLs and bodies

Follow how `test_main.py` patches `httpx.AsyncClient`.

### Scenarios and config models

Import `load_scenarios`, `ScenarioFile`, `load_application_config` from `agentbreak.scenarios` / `agentbreak.config`.

For behaviors, import from `agentbreak.behaviors` and assert on concrete inputs/outputs.

## What to add

1. **New behavior or branch**: at least one happy-path test and one fault/error test.
2. **Bugfix**: a regression test that fails on the old code and passes on the fix.
3. **Public CLI or schema change**: invoke the CLI or load YAML that users would write.

## After writing tests

```bash
pytest -q path/to/new_or_touched_tests.py
agentbreak verify
```

## References

- `tests/test_main.py` -- largest example set
- `tests/test_behaviors.py` -- behavior-focused tests
- `tests/conftest.py`, `tests/helpers.py` -- fixtures and fakes
- `skills/tester/SKILL.md` -- how to run and debug tests
