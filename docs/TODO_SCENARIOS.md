# Deferred Scenario Targets

These scenario targets are recognized by the schema but are not implemented in the current runtime:

- `queue`
- `state`
- `memory`
- `artifact_store`
- `approval`
- `browser_worker`
- `multi_agent`
- `telemetry`

## Planned Follow-Ups

### `queue`
- Duplicate delivery
- Delayed delivery
- Lost acknowledgement

### `state`
- Checkpoint corruption
- Stale checkpoint resume

### `memory`
- Poisoned memory
- Cross-tenant memory leakage
- Stale memory retrieval

### `artifact_store`
- Missing artifact
- Zero-byte artifact
- Stale artifact version

### `approval`
- Stale approval replay
- Expired approval token

### `browser_worker`
- Session expiry
- Wrong-window interaction
- DOM drift

### `multi_agent`
- Delegation cascade
- Shared-state corruption

### `telemetry`
- Missing span
- Missing tool result audit trail
