"""SQLite schema for market data and an auditable paper-trading ledger."""

SCHEMA_VERSION = 1

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS minute_bars (
    symbol TEXT NOT NULL,
    frequency INTEGER NOT NULL,
    bar_time TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    amount REAL NOT NULL,
    adjustflag INTEGER NOT NULL,
    source TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (symbol, frequency, bar_time, adjustflag)
);
CREATE INDEX IF NOT EXISTS idx_minute_date ON minute_bars(frequency, trade_date, bar_time);

CREATE TABLE IF NOT EXISTS download_runs (
    run_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    frequency INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    requested_symbols INTEGER NOT NULL,
    rows_written INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    error TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS strategy_runs (
    run_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    strategy TEXT NOT NULL,
    config_json TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS signals (
    run_id TEXT NOT NULL,
    signal_time TEXT NOT NULL,
    execution_time TEXT NOT NULL,
    symbol TEXT NOT NULL,
    score REAL NOT NULL,
    target_weight REAL NOT NULL,
    PRIMARY KEY (run_id, signal_time, symbol)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    bar_time TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    requested_qty INTEGER NOT NULL,
    filled_qty INTEGER NOT NULL,
    status TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fills (
    fill_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    bar_time TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    gross_value REAL NOT NULL,
    commission REAL NOT NULL,
    tax REAL NOT NULL,
    transfer_fee REAL NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(order_id)
);

CREATE TABLE IF NOT EXISTS position_snapshots (
    run_id TEXT NOT NULL,
    bar_time TEXT NOT NULL,
    symbol TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    available_quantity INTEGER NOT NULL,
    average_cost REAL NOT NULL,
    market_price REAL NOT NULL,
    PRIMARY KEY (run_id, bar_time, symbol)
);

CREATE TABLE IF NOT EXISTS equity_snapshots (
    run_id TEXT NOT NULL,
    bar_time TEXT NOT NULL,
    cash REAL NOT NULL,
    market_value REAL NOT NULL,
    equity REAL NOT NULL,
    drawdown REAL NOT NULL,
    PRIMARY KEY (run_id, bar_time)
);
"""
