"""Transactional SQLite access for recoverable market-data ingestion."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from .config import MarketDataConfig
from .coverage import validate_daily_coverage
from .schema import LISTED_UNIVERSE_SQL, SCHEMA_SQL, SCHEMA_VERSION


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class MarketDataStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            version = connection.execute("SELECT COALESCE(MAX(version),0) FROM market_schema_version").fetchone()[0]
            if version < 2:
                connection.executescript("DROP VIEW IF EXISTS listed_universe;" + LISTED_UNIVERSE_SQL)
            connection.execute(
                "INSERT OR IGNORE INTO market_schema_version(version,applied_at) VALUES (?,?)",
                (SCHEMA_VERSION, now_iso()),
            )

    def upsert_calendar(self, frame: pd.DataFrame) -> int:
        rows = [
            (str(row.calendar_date), int(row.is_trading_day), "BaoStock", now_iso())
            for row in frame.itertuples()
        ]
        with self.connect() as connection:
            connection.executemany(
                "INSERT INTO trade_calendar VALUES (?,?,?,?) ON CONFLICT(calendar_date) DO UPDATE SET is_trading_day=excluded.is_trading_day,source=excluded.source,ingested_at=excluded.ingested_at",
                rows,
            )
        return len(rows)

    def upsert_securities(self, frame: pd.DataFrame) -> int:
        rows = [
            (str(row.code), str(row.code_name), _optional(row.ipoDate), _optional(row.outDate), str(row.type), str(row.status), "BaoStock", now_iso())
            for row in frame.itertuples()
        ]
        sql = """INSERT INTO securities VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(code) DO UPDATE SET
        code_name=excluded.code_name,ipo_date=excluded.ipo_date,out_date=excluded.out_date,
        security_type=excluded.security_type,current_status=excluded.current_status,source=excluded.source,ingested_at=excluded.ingested_at"""
        with self.connect() as connection:
            connection.executemany(sql, rows)
        return len(rows)

    def upsert_observation(self, day: str, frame: pd.DataFrame) -> int:
        rows = [
            (day, str(row.code), str(row.code_name), str(row.tradeStatus), "BaoStock", now_iso())
            for row in frame.itertuples()
        ]
        sql = """INSERT INTO universe_observations VALUES (?,?,?,?,?,?) ON CONFLICT(observation_date,code) DO UPDATE SET
        code_name=excluded.code_name,trade_status=excluded.trade_status,source=excluded.source,ingested_at=excluded.ingested_at"""
        with self.connect() as connection:
            connection.executemany(sql, rows)
        return len(rows)

    def audit_universe(self, day: str, stock_types: list[str], markets: list[str]) -> dict[str, object]:
        placeholders = ",".join("?" for _ in stock_types)
        observed_market_clause = " OR ".join("o.code LIKE ?" for _ in markets)
        derived_market_clause = " OR ".join("code LIKE ?" for _ in markets)
        params = [day, *stock_types, *(f"{market}.%" for market in markets)]
        with self.connect() as connection:
            observed = connection.execute(
                f"""SELECT o.code,o.trade_status,s.out_date FROM universe_observations o JOIN securities s ON s.code=o.code
                WHERE o.observation_date=? AND s.security_type IN ({placeholders}) AND ({observed_market_clause}) ORDER BY o.code""",
                params,
            ).fetchall()
            derived = connection.execute(
                f"""SELECT code FROM listed_universe WHERE trade_date=? AND security_type IN ({placeholders})
                AND ({derived_market_clause}) ORDER BY code""",
                params,
            ).fetchall()
        observed_codes = {str(row["code"]) for row in observed}
        derived_codes = {str(row["code"]) for row in derived}
        boundary = {str(row["code"]) for row in observed if row["out_date"] == day and row["trade_status"] == "0"}
        payload = {
            "observationDate": day,
            "observedStockCount": len(observed_codes),
            "derivedStockCount": len(derived_codes),
            "observedOnlyCount": len(observed_codes - derived_codes),
            "derivedOnlyCount": len(derived_codes - observed_codes),
            "observedSha256": _code_hash(observed_codes),
            "derivedSha256": _code_hash(derived_codes),
        }
        payload["status"] = _universe_verdict(observed_codes, derived_codes, boundary)
        with self.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO universe_audits VALUES (?,?,?,?,?,?,?,?,?)",
                (*payload.values(), now_iso()),
            )
        return payload

    def upsert_daily_bars(self, frame: pd.DataFrame) -> int:
        if frame.empty:
            return 0
        fields = [
            "code", "trade_date", "open", "high", "low", "close", "preclose", "volume", "amount",
            "adjustflag", "turnover", "trade_status", "pct_change", "is_st", "source",
        ]
        rows = [tuple(_scalar(row[field]) for field in fields) + (now_iso(),) for row in frame.to_dict("records")]
        updates = ",".join(f"{field}=excluded.{field}" for field in fields[2:]) + ",ingested_at=excluded.ingested_at"
        sql = f"INSERT INTO daily_bars VALUES ({','.join('?' for _ in range(16))}) ON CONFLICT(code,trade_date,adjustflag) DO UPDATE SET {updates}"
        with self.connect() as connection:
            connection.executemany(sql, rows)
        return len(rows)

    def validate_daily_coverage(self, frame: pd.DataFrame, task: dict[str, object]) -> None:
        with self.connect() as connection:
            validate_daily_coverage(
                connection, frame, str(task["code"]), str(task["start_date"]), str(task["end_date"]),
            )

    def upsert_adjustments(self, frame: pd.DataFrame) -> int:
        if frame.empty:
            return 0
        fields = ["code", "operation_date", "fore_adjust_factor", "back_adjust_factor", "adjust_factor", "source"]
        rows = [tuple(_scalar(row[field]) for field in fields) + (now_iso(),) for row in frame.to_dict("records")]
        sql = """INSERT INTO adjustment_factors VALUES (?,?,?,?,?,?,?) ON CONFLICT(code,operation_date) DO UPDATE SET
        fore_adjust_factor=excluded.fore_adjust_factor,back_adjust_factor=excluded.back_adjust_factor,
        adjust_factor=excluded.adjust_factor,source=excluded.source,ingested_at=excluded.ingested_at"""
        with self.connect() as connection:
            connection.executemany(sql, rows)
        return len(rows)

    def begin_run(self, config: MarketDataConfig, operation: str) -> str:
        run_id = f"market-{uuid.uuid4().hex}"
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO market_download_runs VALUES (?,?,?,?,?,?,?,?,?)",
                (run_id, config.experiment_id, operation, json.dumps(config.as_dict(), ensure_ascii=False), "running", 0, None, now_iso(), None),
            )
        return run_id

    def finish_run(self, run_id: str, rows: int, error: str | None = None) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE market_download_runs SET status=?,rows_written=?,error=?,completed_at=? WHERE run_id=?",
                ("failed" if error else "succeeded", rows, error, now_iso(), run_id),
            )

    def prepare_daily_tasks(self, config: MarketDataConfig) -> int:
        placeholders = ",".join("?" for _ in config.security_types)
        market_clause = " OR ".join("code LIKE ?" for _ in config.markets)
        params = [*config.security_types, *(f"{market}.%" for market in config.markets)]
        with self.connect() as connection:
            securities = [dict(row) for row in connection.execute(
                f"SELECT code,ipo_date,out_date FROM securities WHERE security_type IN ({placeholders}) AND ({market_clause}) ORDER BY code",
                params,
            ).fetchall()]
            if config.benchmark_codes:
                benchmark_placeholders = ",".join("?" for _ in config.benchmark_codes)
                securities.extend(dict(row) for row in connection.execute(
                    f"SELECT code,ipo_date,out_date FROM securities WHERE code IN ({benchmark_placeholders}) ORDER BY code",
                    config.benchmark_codes,
                ).fetchall())
            securities = list({str(row["code"]): row for row in securities}.values())
            rows = []
            for security in securities:
                start = max(config.start, security["ipo_date"] or config.start)
                end = min(config.end, security["out_date"] or config.end)
                if start <= end:
                    rows.append((f"daily:{security['code']}:{start}:{end}", "daily", security["code"], start, end, "pending", 0, 0, None, now_iso()))
            connection.executemany("INSERT OR IGNORE INTO market_download_tasks VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
        return len(rows)

    def reset_interrupted_tasks(self) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE market_download_tasks SET status='pending',last_error='interrupted before completion',updated_at=? WHERE status='running'",
                (now_iso(),),
            )
        return cursor.rowcount

    def reset_interrupted_runs(self) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE market_download_runs SET status='failed',error='interrupted before completion',completed_at=? WHERE status='running'",
                (now_iso(),),
            )
        return cursor.rowcount

    def reset_daily_data(self) -> dict[str, int]:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            bars = int(connection.execute("SELECT COUNT(*) FROM daily_bars").fetchone()[0])
            factors = int(connection.execute("SELECT COUNT(*) FROM adjustment_factors").fetchone()[0])
            tasks = int(connection.execute("SELECT COUNT(*) FROM market_download_tasks WHERE task_type='daily'").fetchone()[0])
            connection.execute("DELETE FROM daily_bars")
            connection.execute("DELETE FROM adjustment_factors")
            connection.execute(
                "UPDATE market_download_tasks SET status='pending',attempts=0,rows_written=0,last_error=NULL,updated_at=? WHERE task_type='daily'",
                (now_iso(),),
            )
            connection.execute(
                "UPDATE market_download_runs SET status='failed',error='superseded: concurrent BaoStock sessions invalidated this attempt',completed_at=? WHERE status='running'",
                (now_iso(),),
            )
        return {"deletedDailyBars": bars, "deletedAdjustmentFactors": factors, "resetTasks": tasks}

    def pending_tasks(self, retries: int, limit: int | None) -> list[dict[str, object]]:
        query = """SELECT * FROM market_download_tasks WHERE task_type='daily'
        AND status IN ('pending','failed') AND attempts < ? ORDER BY task_key"""
        params: list[object] = [retries]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def claim_tasks(self, retries: int, limit: int | None) -> list[dict[str, object]]:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            query = """SELECT * FROM market_download_tasks WHERE task_type='daily'
            AND status IN ('pending','failed') AND attempts < ? ORDER BY task_key"""
            params: list[object] = [retries]
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            tasks = [dict(row) for row in connection.execute(query, params).fetchall()]
            if tasks:
                connection.executemany(
                    "UPDATE market_download_tasks SET status='running',updated_at=? WHERE task_key=?",
                    [(now_iso(), str(task["task_key"])) for task in tasks],
                )
        return tasks

    def mark_task_running(self, task_key: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE market_download_tasks SET status='running',attempts=attempts+1,updated_at=? WHERE task_key=?",
                (now_iso(), task_key),
            )

    def finish_task(self, task_key: str, rows: int, error: str | None = None) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE market_download_tasks SET status=?,rows_written=?,last_error=?,updated_at=? WHERE task_key=?",
                ("failed" if error else "succeeded", rows, error, now_iso(), task_key),
            )

    def status(self) -> dict[str, object]:
        self.initialize()
        with self.connect() as connection:
            connection.execute("BEGIN")
            snapshot_at = now_iso()
            counts = dict(connection.execute(_COUNTS_QUERY).fetchone())
            tasks = [dict(row) for row in connection.execute(
                "SELECT status,COUNT(*) taskCount,SUM(rows_written) rowsWritten FROM market_download_tasks GROUP BY status ORDER BY status"
            ).fetchall()]
            audits = [dict(row) for row in connection.execute(
                "SELECT observation_date observationDate,observed_stock_count observedStockCount,derived_stock_count derivedStockCount,observed_only_count observedOnlyCount,derived_only_count derivedOnlyCount,status FROM universe_audits ORDER BY observation_date"
            ).fetchall()]
            latest = connection.execute(
                "SELECT run_id runId,operation,status,rows_written rowsWritten,error,completed_at completedAt FROM market_download_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
        return {
            **counts,
            "snapshotAt": snapshot_at,
            "database": str(self.path),
            "databaseBytes": self.path.stat().st_size if self.path.exists() else 0,
            "tasks": tasks,
            "audits": audits,
            "latestRun": dict(latest) if latest else None,
        }


def _optional(value: object) -> str | None:
    text = str(value).strip()
    return text or None


def _scalar(value: object) -> object:
    return None if pd.isna(value) else value


def _code_hash(codes: set[str]) -> str:
    return hashlib.sha256("\n".join(sorted(codes)).encode()).hexdigest()


def _universe_verdict(observed: set[str], derived: set[str], boundary: set[str]) -> str:
    if observed == derived:
        return "pass"
    if observed - boundary == derived:
        return "pass_boundary"
    return "mismatch"


_COUNTS_QUERY = """SELECT
(SELECT COUNT(*) FROM trade_calendar) calendarDays,
(SELECT COUNT(*) FROM trade_calendar WHERE is_trading_day=1) tradingDays,
(SELECT COUNT(*) FROM securities) securityCount,
(SELECT COUNT(*) FROM securities WHERE security_type='1') stockCount,
(SELECT COUNT(*) FROM securities WHERE security_type='1' AND out_date IS NOT NULL) delistedStockCount,
(SELECT COUNT(*) FROM universe_observations) universeObservationRows,
(SELECT COUNT(*) FROM daily_bars) dailyBarCount,
(SELECT COUNT(DISTINCT code) FROM daily_bars) dailyBarSymbols,
(SELECT MIN(trade_date) FROM daily_bars) firstDailyBar,
(SELECT MAX(trade_date) FROM daily_bars) lastDailyBar,
(SELECT COUNT(*) FROM adjustment_factors) adjustmentFactorCount"""
