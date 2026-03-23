# Changelog

All notable changes to AgentBreak are documented here.

## [0.1.1] - 2026-03-15

### Added
- `fault_weights` config option for exact per-error-code probabilities
- `latency_p`, `latency_min`, `latency_max` config options for latency injection
- Duplicate request tracking and suspected-loop detection
- `/_agentbreak/requests` endpoint listing recent requests with fingerprint counts
- `brownout` scenario combining error injection and latency
- Config file support (`config.yaml` auto-loaded, `--config` flag for custom path)
- Mock mode (`--mode mock`) returning fake successful completions without upstream calls
- Claude Code slash command and Agent Skills skill

### Changed
- Scorecard now includes `duplicate_requests` and `suspected_loops` fields

## [0.1.0] - 2026-03-10

### Added
- Initial release
- Proxy mode forwarding requests to an OpenAI-compatible upstream
- Failure injection for `400`, `401`, `403`, `404`, `413`, `429`, `500`, `503`
- `--fail-rate`, `--scenario`, `--error-codes` CLI flags
- `/_agentbreak/scorecard` endpoint
- `POST /v1/chat/completions` support
