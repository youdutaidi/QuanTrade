"""Orchestration for reference and daily BaoStock downloads."""

from __future__ import annotations

import json
import time
from pathlib import Path

from .config import MarketDataConfig
from .provider import BaoStockMarketProvider
from .store import MarketDataStore


def initialize_market_store(config: MarketDataConfig, root: Path) -> dict[str, object]:
    store = MarketDataStore(root / config.database_path)
    store.initialize()
    return store.status()


def download_reference(config: MarketDataConfig, root: Path) -> dict[str, object]:
    store = MarketDataStore(root / config.database_path)
    store.initialize()
    run_id = store.begin_run(config, "download-reference")
    rows_written = 0
    try:
        with BaoStockMarketProvider(timeout_seconds=config.request_timeout_seconds) as provider:
            calendar = provider.trade_calendar(config.start, config.end)
            master = provider.security_master()
            rows_written += store.upsert_calendar(calendar)
            rows_written += store.upsert_securities(master)
            audit_results = []
            for day in _audit_dates(config):
                observation = provider.universe(day)
                rows_written += store.upsert_observation(day, observation)
                audit_results.append(store.audit_universe(day, config.security_types, config.markets))
        store.finish_run(run_id, rows_written)
    except Exception as error:
        store.finish_run(run_id, rows_written, repr(error))
        raise
    payload = {"state": "reference-downloaded", "runId": run_id, "rowsWritten": rows_written, "audits": audit_results, **store.status()}
    _write_inventory(config, root, payload)
    return payload


def download_daily(
    config: MarketDataConfig,
    root: Path,
    max_tasks: int | None = None,
    recover: bool = False,
) -> dict[str, object]:
    store = MarketDataStore(root / config.database_path)
    store.initialize()
    if recover:
        store.reset_interrupted_tasks()
        store.reset_interrupted_runs()
    planned = store.prepare_daily_tasks(config)
    tasks = store.claim_tasks(config.retries, max_tasks)
    run_id = store.begin_run(config, "download-daily")
    rows_written = 0
    failures = 0
    try:
        for offset in range(0, len(tasks), config.batch_size):
            batch = tasks[offset : offset + config.batch_size]
            with BaoStockMarketProvider(timeout_seconds=config.request_timeout_seconds) as provider:
                for batch_index, task in enumerate(batch, start=1):
                    index = offset + batch_index
                    key = str(task["task_key"])
                    try:
                        bars = provider.daily_bars(str(task["code"]), str(task["start_date"]), str(task["end_date"]), config.adjustflag)
                        adjustments = provider.adjustment_factors(str(task["code"]), str(task["start_date"]), str(task["end_date"]))
                        written = store.upsert_daily_bars(bars) + store.upsert_adjustments(adjustments)
                        store.finish_task(key, written)
                        rows_written += written
                    except Exception as error:
                        failures += 1
                        store.finish_task(key, 0, repr(error))
                    print(json.dumps({"progress": index, "selectedTasks": len(tasks), "code": task["code"], "rowsWritten": rows_written, "failures": failures}, ensure_ascii=False), flush=True)
            if offset + len(batch) < len(tasks):
                time.sleep(config.batch_pause_seconds)
        store.finish_run(run_id, rows_written)
    except KeyboardInterrupt:
        store.finish_run(run_id, rows_written, "interrupted by operator")
        raise
    except Exception as error:
        store.finish_run(run_id, rows_written, repr(error))
        raise
    payload = {"state": "daily-downloaded", "runId": run_id, "plannedTasks": planned, "selectedTasks": len(tasks), "rowsWritten": rows_written, "failures": failures, **store.status()}
    _write_inventory(config, root, payload)
    return payload


def market_status(config: MarketDataConfig, root: Path) -> dict[str, object]:
    payload = MarketDataStore(root / config.database_path).status()
    _write_inventory(config, root, payload)
    return payload


def _audit_dates(config: MarketDataConfig) -> list[str]:
    return sorted(set([config.start, config.end, *config.audit_dates]))


def _write_inventory(config: MarketDataConfig, root: Path, payload: dict[str, object]) -> None:
    if not config.app_output:
        return
    output = root / config.app_output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
