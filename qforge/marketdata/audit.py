"""Independent structural and semantic checks for the local market database."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import sqlite3
from pathlib import Path

from .config import MarketDataConfig
from .coverage import audit_calendar, audit_daily_coverage
from .store import MarketDataStore


def audit_market_database(config: MarketDataConfig, root: Path) -> dict[str, object]:
    store = MarketDataStore(root / config.database_path)
    store.initialize()
    with store.connect() as connection:
        connection.execute("BEGIN")
        inventory = store.status(connection)
        quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        coverage = audit_daily_coverage(connection, config.adjustflag)
        calendar = audit_calendar(connection, config.start, config.end)
        integrity = _integrity_counts(connection)
    task_counts = {str(item["status"]): int(item["taskCount"]) for item in inventory["tasks"]}
    audits_pass = bool(inventory["audits"]) and all(item["status"] in {"pass", "pass_boundary"} for item in inventory["audits"])
    tasks_complete = task_counts.get("succeeded", 0) > 0 and sum(
        count for status, count in task_counts.items() if status != "succeeded"
    ) == 0
    integrity_pass = quick_check == "ok" and all(value == 0 for value in integrity.values())
    return {
        "experimentId": config.experiment_id,
        "source": "BaoStock anonymous historical API",
        "provenance": {
            "baostockVersion": importlib.metadata.version("baostock"),
            "pythonVersion": platform.python_version(),
            "sqliteVersion": sqlite3.sqlite_version,
            "configSha256": hashlib.sha256(
                json.dumps(config.as_dict(), sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest(),
        },
        "window": {"start": config.start, "end": config.end},
        "adjustflag": config.adjustflag,
        "quickCheck": quick_check,
        "integrity": integrity,
        "coverage": coverage,
        "calendar": calendar,
        "taskCounts": task_counts,
        "universeAuditsPass": audits_pass,
        "tasksComplete": tasks_complete,
        "integrityPass": integrity_pass,
        "dataReady": audits_pass and tasks_complete and integrity_pass and coverage["pass"] and calendar["pass"],
        "inventory": inventory,
    }


def _integrity_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
            "tradableNullOhlc": _count(connection, """SELECT COUNT(*) FROM daily_bars WHERE trade_status=1
                AND (open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL)"""),
            "invalidOhlcEnvelope": _count(connection, """SELECT COUNT(*) FROM daily_bars WHERE trade_status=1 AND
                (high < open OR high < close OR high < low OR low > open OR low > close OR low > high)"""),
            "negativeVolumeOrAmount": _count(connection, "SELECT COUNT(*) FROM daily_bars WHERE volume < 0 OR amount < 0"),
            "barsOnNonTradingDays": _count(connection, """SELECT COUNT(*) FROM daily_bars b LEFT JOIN trade_calendar c
                ON c.calendar_date=b.trade_date WHERE c.calendar_date IS NULL OR c.is_trading_day != 1"""),
            "barsOutsideLifecycle": _count(connection, """SELECT COUNT(*) FROM daily_bars b JOIN securities s ON s.code=b.code
                WHERE b.trade_date < s.ipo_date OR (s.out_date IS NOT NULL AND b.trade_date > s.out_date)"""),
            "unknownSymbols": _count(connection, """SELECT COUNT(*) FROM daily_bars b LEFT JOIN securities s ON s.code=b.code
                WHERE s.code IS NULL"""),
            "tradableBarsOnDelistingDate": _count(connection, """SELECT COUNT(*) FROM daily_bars b
                JOIN securities s ON s.code=b.code WHERE b.trade_date=s.out_date AND b.trade_status=1"""),
            "unknownObservedSymbols": _count(connection, """SELECT COUNT(*) FROM universe_observations o
                LEFT JOIN securities s ON s.code=o.code WHERE s.code IS NULL"""),
            "invalidTradingStatus": _count(connection, """SELECT COUNT(*) FROM daily_bars
                WHERE trade_status IS NULL OR trade_status NOT IN (0,1)"""),
            "invalidAdjustmentFactors": _count(connection, """SELECT COUNT(*) FROM adjustment_factors
                WHERE fore_adjust_factor IS NULL OR fore_adjust_factor<=0
                OR back_adjust_factor IS NULL OR back_adjust_factor<=0
                OR adjust_factor IS NULL OR adjust_factor<=0"""),
            "unknownAdjustmentSymbols": _count(connection, """SELECT COUNT(*) FROM adjustment_factors f
                LEFT JOIN securities s ON s.code=f.code WHERE s.code IS NULL"""),
    }


def _count(connection: sqlite3.Connection, query: str) -> int:
    return int(connection.execute(query).fetchone()[0])
