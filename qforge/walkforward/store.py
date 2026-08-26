"""Append-only SQLite persistence of study evidence, separate from market data."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .specification import StudySpec


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS study_runs (
    run_id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL, config_sha256 TEXT NOT NULL,
    kind TEXT NOT NULL, verified_strategy INTEGER NOT NULL CHECK(verified_strategy=0),
    event_count INTEGER NOT NULL, events_sha256 TEXT NOT NULL, config_json TEXT NOT NULL,
    audit_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS study_ledger_events (
    run_id TEXT NOT NULL REFERENCES study_runs(run_id), sequence INTEGER NOT NULL,
    event_json TEXT NOT NULL, PRIMARY KEY (run_id,sequence)
);
"""


def persist_ledger(path: Path, spec: StudySpec, events: list[dict], audit: dict, kind: str = "synthetic") -> dict:
    if kind not in {"synthetic", "development", "holdout"} or not events:
        raise ValueError("invalid study kind or empty ledger")
    if [row["sequence"] for row in events] != list(range(len(events))):
        raise ValueError("ledger must have contiguous event sequence numbers")
    encoded = [json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) for row in events]
    fingerprint = _event_hash(encoded)
    run_id = f"study-{uuid.uuid4().hex}"
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript(SCHEMA)
        connection.execute("INSERT INTO study_runs VALUES (?,?,?,?,?,?,?,?,?,?)", (
            run_id, spec.values["experiment_id"], spec.sha256, kind, 0, len(events), fingerprint,
            spec.source_json, json.dumps(audit, ensure_ascii=False, allow_nan=False), datetime.now(timezone.utc).isoformat(),
        ))
        connection.executemany("INSERT INTO study_ledger_events VALUES (?,?,?)", [(run_id, index, value) for index, value in enumerate(encoded)])
    return {"runId": run_id, "database": str(path.resolve()), "eventCount": len(events), "eventsSha256": fingerprint,
            "kind": kind, "verifiedStrategy": False}


def load_ledger(path: Path, run_id: str) -> tuple[list[dict], dict]:
    with sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        run = connection.execute("SELECT * FROM study_runs WHERE run_id=?", (run_id,)).fetchone()
        if run is None:
            raise ValueError("unknown ledger run")
        rows = connection.execute("SELECT sequence,event_json FROM study_ledger_events WHERE run_id=? ORDER BY sequence", (run_id,)).fetchall()
    encoded = [row["event_json"] for row in rows]
    if len(rows) != run["event_count"] or [row["sequence"] for row in rows] != list(range(len(rows))) or _event_hash(encoded) != run["events_sha256"]:
        raise ValueError("persisted ledger fingerprint or event count changed")
    return [json.loads(value) for value in encoded], dict(run)


def _event_hash(encoded: list[str]) -> str:
    return hashlib.sha256("\n".join(encoded).encode("utf-8")).hexdigest()
