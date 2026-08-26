"""Separate SQLite archive for raw requests and annual coverage checkpoints."""

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
CREATE TABLE IF NOT EXISTS action_scope (
    singleton INTEGER PRIMARY KEY CHECK (singleton=1),
    scope_sha256 TEXT NOT NULL,
    plan_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS action_tasks (
    code TEXT NOT NULL, year INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','running','succeeded','failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    active_request_id TEXT, last_error TEXT,
    PRIMARY KEY (code,year)
);
CREATE TABLE IF NOT EXISTS action_runs (
    run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, completed_at TEXT,
    status TEXT NOT NULL, input_evidence_json TEXT NOT NULL, error TEXT
);
CREATE TABLE IF NOT EXISTS action_requests (
    request_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES action_runs(run_id),
    code TEXT NOT NULL, year INTEGER NOT NULL, attempt INTEGER NOT NULL,
    status TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT,
    raw_json TEXT, raw_sha256 TEXT, row_count INTEGER, error TEXT,
    FOREIGN KEY (code,year) REFERENCES action_tasks(code,year),
    UNIQUE (code,year,attempt)
);
CREATE TABLE IF NOT EXISTS action_events (
    request_id TEXT NOT NULL REFERENCES action_requests(request_id),
    row_index INTEGER NOT NULL, code TEXT NOT NULL, ex_date TEXT,
    normalized_json TEXT NOT NULL,
    ledger_ready INTEGER NOT NULL DEFAULT 0 CHECK (ledger_ready=0),
    PRIMARY KEY (request_id,row_index)
);
CREATE INDEX IF NOT EXISTS idx_action_tasks_status ON action_tasks(status,attempts,code,year);
CREATE INDEX IF NOT EXISTS idx_action_events_date ON action_events(code,ex_date);
"""
