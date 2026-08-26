from __future__ import annotations

import pandas as pd

from qforge.marketdata.config import MarketDataConfig
from qforge.marketdata.service import _run_daily_tasks


def test_failed_query_recreates_session_and_counts_only_executed_tasks(monkeypatch) -> None:
    import qforge.marketdata.service as module

    sessions = []
    attempts = []
    finished = []

    class Provider:
        def __init__(self, **kwargs):
            sessions.append(1)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def daily_bars(self, code, *args):
            if code == "sh.600000":
                raise RuntimeError("broken session")
            return pd.DataFrame()

        def adjustment_factors(self, *args):
            return pd.DataFrame()

    class Store:
        def mark_task_running(self, key):
            attempts.append(key)

        def upsert_daily_bars(self, frame):
            return 1

        def upsert_adjustments(self, frame):
            return 0

        def finish_task(self, key, rows, error=None):
            finished.append((key, rows, error))

    monkeypatch.setattr(module, "BaoStockMarketProvider", Provider)
    config = MarketDataConfig("test", "market.sqlite", "2020-01-01", "2020-12-31", batch_pause_seconds=0)
    tasks = [{"task_key": code, "code": code, "start_date": config.start, "end_date": config.end} for code in ["sh.600000", "sh.600001"]]
    rows, failures = _run_daily_tasks(config, Store(), tasks)
    assert len(sessions) == 2
    assert len(attempts) == 2
    assert rows == 1 and failures == 1
    assert len(finished) == 2
