"""Integrity checks for the fault catalog.

These walk ``agentbreak/faults/catalog/`` and assert every ``manifest.yaml`` is
well-formed and self-consistent. The registry loader (``discover_catalog``)
deliberately *skips* malformed manifests so a single bad file never breaks the
whole proxy — which is great at runtime but means a typo in a new fault would
silently disappear instead of failing CI. These tests close that gap so fault
contributions fail fast and loud.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from agentbreak.faults import REGISTRY
from agentbreak.faults._primitives import PRIMITIVES
from agentbreak.faults._registry import discover_catalog

CATALOG_DIR = Path(__file__).resolve().parents[1] / "agentbreak" / "faults" / "catalog"

# Keys every manifest must carry. Derived from the existing catalog: these are
# present in 100% of manifests today.
REQUIRED_KEYS = {
    "id",
    "name",
    "category",
    "severity",
    "targets",
    "tags",
    "phase",
    "description",
    "fix_hint",
}

VALID_CATEGORIES = {"reliability", "security", "multi_agent"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_PHASES = {"pre", "post", "custom"}

# Mirror of the Target literal in agentbreak/scenarios.py. Kept permissive so
# faults targeting not-yet-wired surfaces (queue, memory, browser, ...) still
# pass integrity checks.
VALID_TARGETS = {
    "llm_chat",
    "mcp_tool",
    "queue",
    "state",
    "memory",
    "artifact_store",
    "approval",
    "browser_worker",
    "multi_agent",
    "telemetry",
}


def _manifest_paths() -> list[Path]:
    return sorted(CATALOG_DIR.rglob("manifest.yaml"))


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _ident(path: Path) -> str:
    return str(path.relative_to(CATALOG_DIR).parent)


MANIFEST_PATHS = _manifest_paths()


def test_catalog_dir_exists() -> None:
    assert CATALOG_DIR.is_dir(), f"catalog dir not found: {CATALOG_DIR}"


def test_catalog_not_empty() -> None:
    assert MANIFEST_PATHS, "no manifest.yaml files found in catalog"


@pytest.mark.parametrize("path", MANIFEST_PATHS, ids=_ident)
def test_manifest_is_mapping(path: Path) -> None:
    assert isinstance(_load(path), dict), f"{path} does not parse to a mapping"


@pytest.mark.parametrize("path", MANIFEST_PATHS, ids=_ident)
def test_manifest_has_required_keys(path: Path) -> None:
    manifest = _load(path)
    missing = REQUIRED_KEYS - manifest.keys()
    assert not missing, f"{_ident(path)} is missing keys: {sorted(missing)}"


@pytest.mark.parametrize("path", MANIFEST_PATHS, ids=_ident)
def test_manifest_enums_are_valid(path: Path) -> None:
    manifest = _load(path)
    assert manifest["category"] in VALID_CATEGORIES, f"{_ident(path)} bad category: {manifest['category']}"
    assert manifest["severity"] in VALID_SEVERITIES, f"{_ident(path)} bad severity: {manifest['severity']}"
    assert manifest["phase"] in VALID_PHASES, f"{_ident(path)} bad phase: {manifest['phase']}"


@pytest.mark.parametrize("path", MANIFEST_PATHS, ids=_ident)
def test_manifest_targets_are_valid(path: Path) -> None:
    targets = _load(path)["targets"]
    assert isinstance(targets, list) and targets, f"{_ident(path)} targets must be a non-empty list"
    unknown = set(targets) - VALID_TARGETS
    assert not unknown, f"{_ident(path)} has unknown targets: {sorted(unknown)}"


@pytest.mark.parametrize("path", MANIFEST_PATHS, ids=_ident)
def test_id_matches_directory(path: Path) -> None:
    manifest = _load(path)
    assert manifest["id"] == path.parent.name, (
        f"id '{manifest['id']}' does not match directory '{path.parent.name}'"
    )


@pytest.mark.parametrize("path", MANIFEST_PATHS, ids=_ident)
def test_category_matches_directory(path: Path) -> None:
    # Layout is catalog/<category>/<id>/manifest.yaml
    category_dir = path.parent.parent.name
    manifest = _load(path)
    assert manifest["category"] == category_dir, (
        f"{_ident(path)} category '{manifest['category']}' does not match "
        f"parent directory '{category_dir}'"
    )


@pytest.mark.parametrize("path", MANIFEST_PATHS, ids=_ident)
def test_action_or_handler_is_resolvable(path: Path) -> None:
    manifest = _load(path)
    if manifest["phase"] == "custom":
        handler = manifest.get("handler")
        assert handler, f"{_ident(path)} is phase=custom but declares no handler"
        assert (path.parent / handler).exists(), f"{_ident(path)} handler '{handler}' not found"
    else:
        action = manifest.get("action")
        assert action in PRIMITIVES, (
            f"{_ident(path)} action '{action}' is not a known primitive "
            f"({sorted(PRIMITIVES)})"
        )


@pytest.mark.parametrize("path", MANIFEST_PATHS, ids=_ident)
def test_payload_references_resolve(path: Path) -> None:
    params = _load(path).get("params") or {}
    if not params.get("payload_dir"):
        return
    payload_dir = path.parent / "payloads"
    assert payload_dir.is_dir(), f"{_ident(path)} declares payload_dir but {payload_dir} is missing"
    assert any(payload_dir.iterdir()), f"{_ident(path)} payloads/ directory is empty"
    default_payload = params.get("default_payload")
    if default_payload:
        resolved = (payload_dir / f"{default_payload}.txt").exists() or (payload_dir / default_payload).exists()
        assert resolved, f"{_ident(path)} default_payload '{default_payload}' does not resolve in {payload_dir}"


def test_no_duplicate_ids() -> None:
    ids = [_load(path)["id"] for path in MANIFEST_PATHS]
    duplicates = sorted({fault_id for fault_id in ids if ids.count(fault_id) > 1})
    assert not duplicates, f"duplicate fault ids in catalog: {duplicates}"


def test_registry_loads_every_well_formed_manifest() -> None:
    """Every manifest on disk should survive discovery — no silent skips."""
    discovered = discover_catalog()
    manifest_ids = {_load(path)["id"] for path in MANIFEST_PATHS}
    missing = manifest_ids - set(discovered)
    assert not missing, f"these manifests were silently skipped by the loader: {sorted(missing)}"


def test_module_registry_matches_fresh_discovery() -> None:
    """The cached REGISTRY should agree with a fresh scan of the catalog."""
    assert set(REGISTRY) == set(discover_catalog())
