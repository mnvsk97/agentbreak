"""Lightweight SQLite persistence for AgentBreak run history."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = ".agentbreak/history.db"


class RunHistory:
    def __init__(self, db_path: str | None = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    run_label TEXT,
                    llm_scorecard TEXT,
                    mcp_scorecard TEXT,
                    scenarios TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    target TEXT NOT NULL,
                    scenario_name TEXT,
                    fault_kind TEXT,
                    details TEXT,
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def save_run(
        self,
        llm_scorecard: dict | None,
        mcp_scorecard: dict | None,
        scenarios: list[dict] | None = None,
        label: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO runs (timestamp, run_label, llm_scorecard, mcp_scorecard, scenarios, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    time.time(),
                    label,
                    json.dumps(llm_scorecard),
                    json.dumps(mcp_scorecard),
                    json.dumps(scenarios),
                    json.dumps(metadata),
                ),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def save_failure(
        self,
        run_id: int,
        target: str,
        scenario_name: str | None,
        fault_kind: str | None,
        details: dict | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO failures (run_id, timestamp, target, scenario_name, fault_kind, details) VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, time.time(), target, scenario_name, fault_kind, json.dumps(details)),
            )

    def get_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if row is None:
                return None
            result = self._row_to_dict(row)
            failures = conn.execute(
                "SELECT * FROM failures WHERE run_id = ? ORDER BY timestamp", (run_id,)
            ).fetchall()
            result["failures"] = [self._row_to_dict(f) for f in failures]
            return result

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        for key in ("llm_scorecard", "mcp_scorecard", "scenarios", "metadata", "details"):
            if key in d and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d
