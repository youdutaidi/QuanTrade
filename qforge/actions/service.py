"""Bounded, single-session ingestion; raw capture never promotes a strategy."""

from __future__ import annotations

import json
import hashlib
import time
from importlib.metadata import version
from pathlib import Path

from ..marketdata.provider import BaoStockMarketProvider
from ..marketdata.session import FileLock
from .config import ActionConfig
from .planning import action_plan, admit_action_input
from .store import ActionStore


def download_actions(config: ActionConfig, root: Path, max_tasks: int | None = None) -> dict:
    if max_tasks is not None and max_tasks < 1:
        raise ValueError("max-tasks must be positive")
    database = (root / config.database_path).resolve()
    with FileLock(str(database) + ".job.lock"):
        evidence = admit_action_input(config, root)
        plan = action_plan(config, root)
        store = ActionStore(database)
        store.initialize(plan)
        recovered = store.recover()
        tasks = store.pending_tasks(config.retries, max_tasks)
        run_id = store.begin_run({"dailyInput": evidence, "scopeSha256": plan["scopeSha256"],
                                  "sourceIdentity": capture_identity()})
        try:
            counts = execute_tasks(config, store, run_id, tasks)
            store.finish_run(run_id)
        except BaseException as error:
            store.finish_run(run_id, repr(error))
            raise
        return {**store.status(), **counts, "runId": run_id, "recoveredTasks": recovered}


def capture_identity() -> dict:
    package = Path(__file__).resolve().parent
    paths = sorted(package.glob("*.py")) + [package.parent / "marketdata" / name for name in ("provider.py", "session.py")]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(package.parent)).encode() + b"\0" + path.read_bytes() + b"\0")
    return {"provider": "BaoStock", "providerVersion": version("baostock"), "adapterSha256": digest.hexdigest()}


def execute_tasks(config: ActionConfig, store: ActionStore, run_id: str, tasks: list[dict]) -> dict:
    index = rows = failures = 0
    while index < len(tasks):
        with BaoStockMarketProvider(timeout_seconds=config.request_timeout_seconds) as provider:
            for _ in range(config.batch_size):
                if index == len(tasks):
                    break
                task = tasks[index]
                request_id = store.start_request(task, run_id)
                failed = False
                try:
                    frame = provider.dividends(task["code"], task["year"])
                    rows += store.save_response(request_id, frame)
                except Exception as error:
                    store.fail_request(request_id, repr(error))
                    failures += 1
                    failed = True
                index += 1
                print(json.dumps({"progress": index, "selectedTasks": len(tasks), **task,
                                  "rowsWritten": rows, "failures": failures}), flush=True)
                if failed:
                    break
        if index < len(tasks):
            time.sleep(config.batch_pause_seconds)
    return {"attemptedTasks": index, "rowsWritten": rows, "failures": failures}
