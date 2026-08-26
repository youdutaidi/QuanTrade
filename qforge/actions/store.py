"""Transactional ownership of raw action requests, failures and resumable tasks."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .normalization import NORMALIZATION_VERSION, normalize_response
from .schema import SCHEMA_SQL


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class ActionStore:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()

    @contextmanager
    def connect(self, readonly: bool = False):
        target = self.path.as_uri() + "?mode=ro" if readonly else str(self.path)
        conn = sqlite3.connect(target, uri=readonly, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def initialize(self, plan: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            if any(not table.startswith("action_") for table in tables):
                raise ValueError("refusing to initialize an action archive inside another database")
            conn.executescript(SCHEMA_SQL)
            scope = conn.execute("SELECT scope_sha256 FROM action_scope").fetchone()
            if scope and scope[0] != plan["scopeSha256"]:
                raise ValueError("action scope changed; use a separate archive for a different plan")
            conn.execute("INSERT OR IGNORE INTO action_scope VALUES(1,?,?)", (plan["scopeSha256"], encode(plan)))
            conn.executemany("INSERT OR IGNORE INTO action_tasks(code,year,status) VALUES(?,?,'pending')",
                             [(task["code"], task["year"]) for task in plan["tasks"]])

    def recover(self) -> int:
        with self.connect() as conn:
            count = conn.execute("UPDATE action_tasks SET status='failed',last_error='interrupted' WHERE status='running'").rowcount
            conn.execute("UPDATE action_requests SET status='interrupted',error='interrupted',completed_at=? WHERE status='running'", (utc_now(),))
            conn.execute("UPDATE action_runs SET status='interrupted',error='interrupted',completed_at=? WHERE status='running'", (utc_now(),))
        return count

    def begin_run(self, evidence: dict) -> str:
        run_id = f"actions-{uuid.uuid4().hex}"
        with self.connect() as conn:
            conn.execute("INSERT INTO action_runs VALUES(?,?,NULL,'running',?,NULL)", (run_id, utc_now(), encode(evidence)))
        return run_id

    def finish_run(self, run_id: str, error: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE action_runs SET status=?,error=?,completed_at=? WHERE run_id=? AND status='running'",
                         ("failed" if error else "finished", error, utc_now(), run_id))

    def pending_tasks(self, retries: int, limit: int | None) -> list[dict]:
        with self.connect(readonly=True) as conn:
            rows = conn.execute("SELECT code,year FROM action_tasks WHERE status IN ('pending','failed') AND attempts<? ORDER BY code,year LIMIT ?",
                                (retries, limit if limit is not None else -1)).fetchall()
        return [dict(row) for row in rows]

    def start_request(self, task: dict, run_id: str) -> str:
        request_id = f"request-{uuid.uuid4().hex}"
        with self.connect() as conn:
            count = conn.execute("UPDATE action_tasks SET status='running',attempts=attempts+1,active_request_id=?,last_error=NULL WHERE code=? AND year=? AND status IN ('pending','failed')",
                                 (request_id, task["code"], task["year"])).rowcount
            if count != 1:
                raise ValueError("action task is already running or completed")
            attempt = conn.execute("SELECT attempts FROM action_tasks WHERE code=? AND year=?", (task["code"], task["year"])).fetchone()[0]
            conn.execute("INSERT INTO action_requests(request_id,run_id,code,year,attempt,status,started_at) VALUES(?,?,?,?,?,'running',?)",
                         (request_id, run_id, task["code"], task["year"], attempt, utc_now()))
        return request_id

    def save_response(self, request_id: str, frame: pd.DataFrame) -> int:
        with self.connect() as conn:
            request = conn.execute("SELECT * FROM action_requests WHERE request_id=? AND status='running'", (request_id,)).fetchone()
            if request is None:
                raise ValueError("action request is not active")
            raw, events = normalize_response(frame, request["code"], request["year"])
            encoded = encode(raw)
            fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
            conn.execute("UPDATE action_requests SET status='succeeded',raw_json=?,raw_sha256=?,row_count=?,completed_at=? WHERE request_id=?",
                         (encoded, fingerprint, len(events), utc_now(), request_id))
            conn.executemany("INSERT INTO action_events VALUES(?,?,?,?,?,0)",
                             [(request_id, index, event["code"], event["ex_date"], encode(event)) for index, event in enumerate(events)])
            changed = conn.execute("UPDATE action_tasks SET status='succeeded',last_error=NULL WHERE active_request_id=? AND status='running'", (request_id,)).rowcount
            if changed != 1:
                raise ValueError("action task ownership changed")
        return len(events)

    def fail_request(self, request_id: str, error: str) -> None:
        with self.connect() as conn:
            changed = conn.execute("UPDATE action_requests SET status='failed',error=?,completed_at=? WHERE request_id=? AND status='running'",
                                   (error, utc_now(), request_id)).rowcount
            if changed != 1:
                raise ValueError("cannot replace a completed action request")
            conn.execute("UPDATE action_tasks SET status='failed',last_error=? WHERE active_request_id=? AND status='running'", (error, request_id))

    def raw_response(self, request_id: str) -> dict:
        with self.connect(readonly=True) as conn:
            row = conn.execute("SELECT raw_json,raw_sha256 FROM action_requests WHERE request_id=? AND status='succeeded'", (request_id,)).fetchone()
        if row is None or hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
            raise ValueError("raw action response is absent or its hash changed")
        return json.loads(row[0])

    def normalized_response(self, request_id: str) -> dict:
        """Reparse hash-verified raw bytes without replacing any historical projection."""
        raw = self.raw_response(request_id)
        frame = pd.DataFrame(raw["rows"], columns=raw["fields"])
        frame.attrs["request"] = raw["request"]
        request = raw["request"]
        _, events = normalize_response(frame, request["code"], request["year"])
        return {"requestId": request_id, "normalizationVersion": NORMALIZATION_VERSION,
                "request": request, "events": events}

    def status(self) -> dict:
        if not self.path.exists():
            return {"state": "not-initialized", "database": str(self.path), "ledgerReady": False}
        with self.connect(readonly=True) as conn:
            conn.execute("BEGIN")
            counts = {row[0]: row[1] for row in conn.execute("SELECT status,COUNT(*) FROM action_tasks GROUP BY status")}
            events = conn.execute("SELECT COUNT(*) FROM action_events").fetchone()[0]
            empty = conn.execute("SELECT COUNT(*) FROM action_requests WHERE status='succeeded' AND row_count=0").fetchone()[0]
            requests = conn.execute("SELECT COUNT(*) FROM action_requests").fetchone()[0]
            scope = conn.execute("SELECT scope_sha256 FROM action_scope").fetchone()[0]
        complete = bool(counts) and set(counts) == {"succeeded"}
        return {"state": "source-capture-complete" if complete else "incomplete", "database": str(self.path),
                "scopeSha256": scope, "tasks": counts, "events": events, "requests": requests,
                "queriedEmptyYears": empty, "ledgerReady": False, "investorTaxVerified": False}
