from __future__ import annotations

import pandas as pd
import pytest

from qforge.marketdata.audit import audit_market_database
from qforge.marketdata.config import MarketDataConfig
from qforge.marketdata.coverage import audit_daily_coverage
from qforge.marketdata.store import MarketDataStore


def fixture_store(tmp_path, out_date=""):
    config = MarketDataConfig("coverage-test", "market.sqlite", "2020-01-02", "2020-01-06")
    store = MarketDataStore(tmp_path / config.database_path)
    store.initialize()
    store.upsert_calendar(pd.DataFrame([
        {"calendar_date": day, "is_trading_day": int(day not in {"2020-01-04", "2020-01-05"})}
        for day in ["2020-01-02", "2020-01-03", "2020-01-04", "2020-01-05", "2020-01-06"]
    ]))
    store.upsert_securities(pd.DataFrame([{
        "code": "sh.600000", "code_name": "样本", "ipoDate": "1999-01-01", "outDate": out_date, "type": "1", "status": "1",
    }]))
    store.upsert_observation(config.start, pd.DataFrame([{"code": "sh.600000", "code_name": "样本", "tradeStatus": "1"}]))
    store.audit_universe(config.start, ["1"], ["sh", "sz"])
    store.prepare_daily_tasks(config)
    task = store.pending_tasks(3, None)[0]
    return config, store, task


def raw_frame(days, status=1):
    return pd.DataFrame([{
        "code": "sh.600000", "trade_date": day, "open": 10, "high": 10, "low": 10, "close": 10,
        "preclose": 10, "volume": 100, "amount": 1000, "adjustflag": 3, "turnover": 1,
        "trade_status": status, "pct_change": 0, "is_st": 0, "source": "BaoStock",
    } for day in days])


def test_success_checkpoint_cannot_hide_missing_middle_day(tmp_path):
    config, store, task = fixture_store(tmp_path)
    bars = raw_frame(["2020-01-02", "2020-01-06"])
    with pytest.raises(ValueError, match="missing dates"):
        store.validate_daily_coverage(bars, task)
    store.upsert_daily_bars(bars)
    store.finish_task(task["task_key"], 2)
    report = audit_market_database(config, tmp_path)
    assert report["tasksComplete"] is True
    assert report["coverage"]["missingRows"] == 1
    assert report["coverage"]["examples"][0]["first_missing_date"] == "2020-01-03"
    assert report["dataReady"] is False


def test_empty_success_is_not_data_ready(tmp_path):
    config, store, task = fixture_store(tmp_path)
    store.finish_task(task["task_key"], 0)
    report = audit_market_database(config, tmp_path)
    assert report["coverage"]["missingRows"] == 3
    assert report["dataReady"] is False


def test_delisting_date_is_optional_nontradable_source_boundary(tmp_path):
    config, store, task = fixture_store(tmp_path, out_date="2020-01-06")
    bars = raw_frame(["2020-01-02", "2020-01-03"])
    store.validate_daily_coverage(bars, task)
    store.upsert_daily_bars(bars)
    store.finish_task(task["task_key"], 2)
    with store.connect() as connection:
        assert audit_daily_coverage(connection, 3)["pass"] is True
        assert connection.execute("SELECT COUNT(*) FROM listed_universe WHERE trade_date='2020-01-06'").fetchone()[0] == 0
    store.upsert_daily_bars(raw_frame(["2020-01-06"], status=0))
    report = audit_market_database(config, tmp_path)
    assert report["coverage"]["optionalSuspendedDelistingRows"] == 1
    assert report["dataReady"] is True
    store.upsert_daily_bars(raw_frame(["2020-01-06"], status=1))
    assert audit_market_database(config, tmp_path)["dataReady"] is False


def test_missing_calendar_cannot_make_missing_bar_invisible(tmp_path):
    config, store, task = fixture_store(tmp_path)
    store.upsert_daily_bars(raw_frame(["2020-01-02", "2020-01-06"]))
    store.finish_task(task["task_key"], 2)
    with store.connect() as connection:
        connection.execute("DELETE FROM trade_calendar WHERE calendar_date='2020-01-03'")
    report = audit_market_database(config, tmp_path)
    assert report["coverage"]["pass"] is True
    assert report["calendar"]["missingDays"] == 1
    assert report["dataReady"] is False
