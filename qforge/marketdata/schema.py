"""SQLite schema for reference data, point-in-time universes, and daily bars."""

SCHEMA_VERSION = 2

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS market_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trade_calendar (
    calendar_date TEXT PRIMARY KEY,
    is_trading_day INTEGER NOT NULL,
    source TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS securities (
    code TEXT PRIMARY KEY,
    code_name TEXT NOT NULL,
    ipo_date TEXT,
    out_date TEXT,
    security_type TEXT NOT NULL,
    current_status TEXT NOT NULL,
    source TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_security_lifecycle
ON securities(security_type, ipo_date, out_date);

CREATE TABLE IF NOT EXISTS universe_observations (
    observation_date TEXT NOT NULL,
    code TEXT NOT NULL,
    code_name TEXT NOT NULL,
    trade_status TEXT NOT NULL,
    source TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (observation_date, code)
);

CREATE TABLE IF NOT EXISTS universe_audits (
    observation_date TEXT PRIMARY KEY,
    observed_stock_count INTEGER NOT NULL,
    derived_stock_count INTEGER NOT NULL,
    observed_only_count INTEGER NOT NULL,
    derived_only_count INTEGER NOT NULL,
    observed_sha256 TEXT NOT NULL,
    derived_sha256 TEXT NOT NULL,
    status TEXT NOT NULL,
    checked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_bars (
    code TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    preclose REAL,
    volume REAL,
    amount REAL,
    adjustflag INTEGER NOT NULL,
    turnover REAL,
    trade_status INTEGER,
    pct_change REAL,
    is_st INTEGER,
    source TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (code, trade_date, adjustflag)
);
CREATE INDEX IF NOT EXISTS idx_daily_bars_date
ON daily_bars(trade_date, code, adjustflag);

CREATE TABLE IF NOT EXISTS adjustment_factors (
    code TEXT NOT NULL,
    operation_date TEXT NOT NULL,
    fore_adjust_factor REAL,
    back_adjust_factor REAL,
    adjust_factor REAL,
    source TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (code, operation_date)
);

CREATE TABLE IF NOT EXISTS market_download_runs (
    run_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    config_json TEXT NOT NULL,
    status TEXT NOT NULL,
    rows_written INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS market_download_tasks (
    task_key TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    code TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    rows_written INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_market_tasks_status
ON market_download_tasks(task_type, status, attempts, task_key);

"""

LISTED_UNIVERSE_SQL = """CREATE VIEW IF NOT EXISTS listed_universe AS
SELECT c.calendar_date AS trade_date,
       s.code,
       s.code_name,
       s.security_type
FROM trade_calendar AS c
JOIN securities AS s
  ON c.is_trading_day = 1
 AND s.ipo_date IS NOT NULL
 AND s.ipo_date <= c.calendar_date
 AND (s.out_date IS NULL OR s.out_date = '' OR s.out_date > c.calendar_date);
"""

SCHEMA_SQL += LISTED_UNIVERSE_SQL
