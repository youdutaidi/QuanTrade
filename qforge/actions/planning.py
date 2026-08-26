"""Read-only lifecycle planning and admission before any action source request."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from ..marketdata.admission import verify_completed_panel
from ..marketdata.config import MarketDataConfig
from .config import ActionConfig


def lifecycle_tasks(securities: list[dict], start: str, end: str) -> list[dict]:
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last:
        raise ValueError("action window is reversed")
    tasks = []
    for security in securities:
        code = security["code"]
        if str(security["security_type"]) != "1" or not code.startswith(("sh.60", "sh.68", "sz.00", "sz.30")):
            continue
        if not security["ipo_date"]:
            raise ValueError(f"missing IPO date for {code}")
        lower = max(first, date.fromisoformat(security["ipo_date"]))
        upper = last
        if security["out_date"]:
            upper = min(upper, date.fromisoformat(security["out_date"]) - timedelta(days=1))
        if lower <= upper:
            tasks.extend({"code": code, "year": year} for year in range(lower.year, upper.year + 1))
    keys = [(task["code"], task["year"]) for task in tasks]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate security lifecycle rows")
    return sorted(tasks, key=lambda task: (task["code"], task["year"]))


def action_plan(config: ActionConfig, root: Path) -> dict:
    market = MarketDataConfig.from_json(root / config.market_config)
    if market.adjustflag != 3 or market.security_types != ["1"] or set(market.markets) != {"sh", "sz"}:
        raise ValueError("action archive requires raw Shanghai/Shenzhen stock lifecycle scope")
    path = (root / market.database_path).resolve()
    if path == (root / config.database_path).resolve():
        raise ValueError("action archive must not share the daily database path")
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        securities = [dict(row) for row in conn.execute("SELECT * FROM securities ORDER BY code")]
    tasks = lifecycle_tasks(securities, market.start, market.end)
    if not tasks:
        raise ValueError("action lifecycle plan is empty")
    scope = {"config": config.as_dict(), "start": market.start, "end": market.end,
             "yearType": "operate", "tasks": tasks}
    encoded = json.dumps(scope, sort_keys=True, separators=(",", ":"))
    return {**scope, "scopeSha256": hashlib.sha256(encoded.encode()).hexdigest(),
            "state": "preview-only", "sourceRequests": 0,
            "symbols": len({task["code"] for task in tasks}), "taskCount": len(tasks),
            "claim": "lifecycle plan only; no action coverage or economic P&L admission"}


def admit_action_input(config: ActionConfig, root: Path) -> dict:
    market = MarketDataConfig.from_json(root / config.market_config)
    path = (root / market.database_path).resolve()
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as conn:
        running = conn.execute("SELECT COUNT(*) FROM market_download_runs WHERE status='running'").fetchone()[0]
    if running:
        raise ValueError("daily source job is still running; action ingestion is not admitted")
    manifest = (root / market.audit_output).parent / "data_completion.json"
    return verify_completed_panel(manifest, market)
