"""Transactional access to the local minute-market and paper-ledger database."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from .config import MinuteConfig
from .schema import SCHEMA_SQL, SCHEMA_VERSION


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class MinuteStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            connection.execute(
                "INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, now_iso()),
            )

    def upsert_bars(self, frame: pd.DataFrame) -> int:
        if frame.empty:
            return 0
        required = {"symbol", "frequency", "bar_time", "trade_date", "open", "high", "low", "close", "volume", "amount", "adjustflag", "source"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"minute bars missing columns: {sorted(missing)}")
        rows = [_bar_tuple(row) for row in frame.to_dict("records")]
        with self.connect() as connection:
            connection.executemany(_BAR_UPSERT, rows)
        return len(rows)

    def load_bars(self, config: MinuteConfig) -> pd.DataFrame:
        placeholders = ",".join("?" for _ in config.symbols)
        query = f"""SELECT symbol, frequency, bar_time, trade_date, open, high, low, close, volume, amount, adjustflag
                    FROM minute_bars WHERE frequency=? AND adjustflag=? AND trade_date BETWEEN ? AND ?
                    AND symbol IN ({placeholders}) ORDER BY bar_time, symbol"""
        params = [config.frequency, config.adjustflag, config.start, config.end, *config.symbols]
        with self.connect() as connection:
            frame = pd.read_sql_query(query, connection, params=params)
        if not frame.empty:
            frame["bar_time"] = pd.to_datetime(frame["bar_time"])
            frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.date
        return frame

    def begin_download(self, config: MinuteConfig) -> str:
        run_id = f"download-{uuid.uuid4().hex}"
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO download_runs(run_id,provider,frequency,start_date,end_date,requested_symbols,status,started_at) VALUES (?,?,?,?,?,?,?,?)",
                (run_id, "BaoStock", config.frequency, config.start, config.end, len(config.symbols), "running", now_iso()),
            )
        return run_id

    def finish_download(self, run_id: str, rows: int, error: str | None = None) -> None:
        status = "failed" if error else "succeeded"
        with self.connect() as connection:
            connection.execute(
                "UPDATE download_runs SET rows_written=?,status=?,error=?,completed_at=? WHERE run_id=?",
                (rows, status, error, now_iso(), run_id),
            )

    def begin_strategy(self, config: MinuteConfig) -> str:
        run_id = f"strategy-{uuid.uuid4().hex}"
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO strategy_runs(run_id,experiment_id,strategy,config_json,status,started_at) VALUES (?,?,?,?,?,?)",
                (run_id, config.experiment_id, config.strategy, json.dumps(config.as_dict(), ensure_ascii=False), "running", now_iso()),
            )
        return run_id

    def finish_strategy(self, run_id: str, error: str | None = None) -> None:
        status = "failed" if error else "succeeded"
        with self.connect() as connection:
            connection.execute(
                "UPDATE strategy_runs SET status=?,error=?,completed_at=? WHERE run_id=?",
                (status, error, now_iso(), run_id),
            )

    def write_signals(self, run_id: str, frame: pd.DataFrame) -> None:
        rows = [
            (run_id, str(row.signal_time), str(row.execution_time), row.symbol, float(row.score), float(row.target_weight))
            for row in frame.itertuples()
        ]
        with self.connect() as connection:
            connection.executemany("INSERT OR REPLACE INTO signals VALUES (?,?,?,?,?,?)", rows)

    def write_order(self, order: dict[str, object]) -> None:
        fields = ("order_id", "run_id", "bar_time", "symbol", "side", "requested_qty", "filled_qty", "status", "reason", "created_at")
        with self.connect() as connection:
            connection.execute(f"INSERT INTO orders({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})", tuple(order.get(field) for field in fields))

    def write_fill(self, fill: dict[str, object]) -> None:
        fields = ("fill_id", "order_id", "run_id", "bar_time", "symbol", "side", "quantity", "price", "gross_value", "commission", "tax", "transfer_fee")
        with self.connect() as connection:
            connection.execute(f"INSERT INTO fills({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})", tuple(fill[field] for field in fields))

    def write_snapshot(self, run_id: str, bar_time: pd.Timestamp, broker: object, prices: dict[str, float]) -> None:
        positions = broker.position_records(run_id, bar_time, prices)
        equity = broker.equity_record(run_id, bar_time, prices)
        with self.connect() as connection:
            connection.executemany("INSERT OR REPLACE INTO position_snapshots VALUES (?,?,?,?,?,?,?)", positions)
            connection.execute("INSERT OR REPLACE INTO equity_snapshots VALUES (?,?,?,?,?,?)", equity)

    def status(self) -> dict[str, object]:
        self.initialize()
        with self.connect() as connection:
            bars = dict(connection.execute(_STATUS_QUERY).fetchone())
            downloads = connection.execute("SELECT run_id,status,rows_written,completed_at,error FROM download_runs ORDER BY started_at DESC LIMIT 1").fetchone()
            strategies = connection.execute("SELECT run_id,status,completed_at,error FROM strategy_runs ORDER BY started_at DESC LIMIT 1").fetchone()
        return {
            **bars,
            "databaseBytes": self.path.stat().st_size if self.path.exists() else 0,
            "lastDownload": dict(downloads) if downloads else None,
            "lastStrategy": dict(strategies) if strategies else None,
        }

    def load_equity(self, run_id: str) -> pd.DataFrame:
        with self.connect() as connection:
            frame = pd.read_sql_query(
                "SELECT bar_time,cash,market_value,equity,drawdown FROM equity_snapshots WHERE run_id=? ORDER BY bar_time",
                connection,
                params=[run_id],
            )
        if not frame.empty:
            frame["bar_time"] = pd.to_datetime(frame["bar_time"])
        return frame

    def ledger_summary(self, run_id: str) -> dict[str, object]:
        with self.connect() as connection:
            orders = dict(connection.execute(
                "SELECT COUNT(*) orderCount,SUM(filled_qty) filledShares,SUM(status='rejected') rejectedOrders,SUM(status='partial') partialOrders FROM orders WHERE run_id=?",
                (run_id,),
            ).fetchone())
            fills = dict(connection.execute(
                "SELECT COUNT(*) fillCount,COALESCE(SUM(gross_value),0) grossTurnover,COALESCE(SUM(commission+tax+transfer_fee),0) explicitCosts FROM fills WHERE run_id=?",
                (run_id,),
            ).fetchone())
        return {**orders, **fills}

    def recent_orders(self, run_id: str, limit: int = 12) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT bar_time,symbol,side,requested_qty,filled_qty,status,reason FROM orders WHERE run_id=? ORDER BY bar_time DESC LIMIT ?",
                (run_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]


def _bar_tuple(row: dict[str, object]) -> tuple[object, ...]:
    bar_time = pd.Timestamp(row["bar_time"]).isoformat(sep=" ")
    return (
        str(row["symbol"]), int(row["frequency"]), bar_time, str(row["trade_date"]),
        float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]),
        float(row["volume"]), float(row["amount"]), int(row["adjustflag"]), str(row["source"]), now_iso(),
    )


_BAR_UPSERT = """INSERT INTO minute_bars VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
ON CONFLICT(symbol,frequency,bar_time,adjustflag) DO UPDATE SET
trade_date=excluded.trade_date,open=excluded.open,high=excluded.high,low=excluded.low,
close=excluded.close,volume=excluded.volume,amount=excluded.amount,source=excluded.source,ingested_at=excluded.ingested_at"""

_STATUS_QUERY = """SELECT COUNT(*) AS barCount, COUNT(DISTINCT symbol) AS symbolCount,
MIN(bar_time) AS firstBar, MAX(bar_time) AS lastBar, COUNT(DISTINCT trade_date) AS tradeDays
FROM minute_bars"""
