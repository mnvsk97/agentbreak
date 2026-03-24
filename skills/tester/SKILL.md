---
name: tester
description: Run or debug tests for AgentBreak -- pytest, agentbreak verify, verify --live, interpreting failures, and keeping runs deterministic.
---

# Tester

Use this skill to run tests, triage failures, or confirm a change is safe.

## Run tests

```bash
pip install -e '.[dev]'

# Unit/integration suite
pytest -q

# Same thing via the CLI entrypoint
agentbreak verify

# Full LangGraph + mock OpenAI + MCP stack (slower, needs example deps)
agentbreak verify --live
```

## Focused runs

```bash
pytest -q tests/test_main.py
pytest -q tests/test_behaviors.py
pytest -q -k "some_keyword"
pytest -q --lf          # last failed
pytest -q -x            # stop on first failure
pytest -vv --tb=long    # verbose tracebacks
```

## Debugging failures

1. **Import / collection errors**: run `pytest --collect-only -q`.
2. **Global state**: `tests/conftest.py` resets `main.service_state` and `DummyAsyncClient` each test. If a test mutates other globals, reset them in the test.
3. **Async / HTTP**: upstream LLM calls use `tests.helpers.DummyAsyncClient` (patched over `httpx.AsyncClient`). Set `DummyAsyncClient.responses`, `error`, or `response` before the code under test runs.
4. **CLI tests**: use `typer.testing.CliRunner` with `runner.invoke(main.cli, [...])`.
5. **HTTP app tests**: use `fastapi.testclient.TestClient` against `main.app` with `main.service_state` set.

## Reporting

Summarize:

- Command(s) run and exit code
- Failing test names and one-line cause
- Whether the failure is flaky (timing, random scenarios) or deterministic

## References

- `tests/conftest.py` -- autouse fixtures
- `tests/helpers.py` -- `DummyAsyncClient`, `DummyResponse`
- `CONTRIBUTING.md` -- verify commands
- `docs/live-testing.md` -- live harness details
