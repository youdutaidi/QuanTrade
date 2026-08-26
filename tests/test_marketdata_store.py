from __future__ import annotations

import sqlite3

import pandas as pd

from qforge.marketdata.config import MarketDataConfig
from qforge.marketdata.store import MarketDataStore


def config(path: str) -> MarketDataConfig:
    return MarketDataConfig(
        experiment_id="test",
        database_path=path,
        start="2020-01-01",
        end="2021-12-31",
        audit_dates=["2020-06-01"],
    )


def test_lifecycle_view_keeps_delisted_stock_before_exit(tmp_path) -> None:
    store = MarketDataStore(tmp_path / "market.sqlite")
    store.initialize()
    store.upsert_calendar(pd.DataFrame([
        {"calendar_date": "2020-06-01", "is_trading_day": "1"},
        {"calendar_date": "2021-06-01", "is_trading_day": "1"},
    ]))
    store.upsert_securities(pd.DataFrame([
        {"code": "sh.600001", "code_name": "退市样本", "ipoDate": "1998-01-01", "outDate": "2020-12-31", "type": "1", "status": "0"},
        {"code": "sz.000001", "code_name": "存续样本", "ipoDate": "1991-01-01", "outDate": "", "type": "1", "status": "1"},
    ]))
    with store.connect() as connection:
        before = [row[0] for row in connection.execute("SELECT code FROM listed_universe WHERE trade_date='2020-06-01' ORDER BY code")]
        after = [row[0] for row in connection.execute("SELECT code FROM listed_universe WHERE trade_date='2021-06-01' ORDER BY code")]
    assert before == ["sh.600001", "sz.000001"]
    assert after == ["sz.000001"]


def test_universe_audit_qualifies_joined_code_column(tmp_path) -> None:
    store = MarketDataStore(tmp_path / "market.sqlite")
    store.initialize()
    store.upsert_calendar(pd.DataFrame([{"calendar_date": "2020-06-01", "is_trading_day": "1"}]))
    store.upsert_securities(pd.DataFrame([{
        "code": "sh.600001", "code_name": "样本", "ipoDate": "1998-01-01", "outDate": "", "type": "1", "status": "1",
    }]))
    store.upsert_observation("2020-06-01", pd.DataFrame([{
        "code": "sh.600001", "tradeStatus": "1", "code_name": "样本",
    }]))
    audit = store.audit_universe("2020-06-01", ["1"], ["sh", "sz"])
    assert audit["status"] == "pass"
    assert audit["observedStockCount"] == 1


def test_daily_upsert_is_idempotent(tmp_path) -> None:
    store = MarketDataStore(tmp_path / "market.sqlite")
    store.initialize()
    frame = pd.DataFrame([{
        "code": "sh.600000", "trade_date": "2020-01-02", "open": 10, "high": 11, "low": 9, "close": 10.5,
        "preclose": 10, "volume": 1000, "amount": 10000, "adjustflag": 3, "turnover": 1.2,
        "trade_status": 1, "pct_change": 5, "is_st": 0, "source": "BaoStock",
    }])
    store.upsert_daily_bars(frame)
    frame.loc[0, "close"] = 10.6
    store.upsert_daily_bars(frame)
    with store.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM daily_bars").fetchone()[0] == 1
        assert connection.execute("SELECT close FROM daily_bars").fetchone()[0] == 10.6


def test_interrupted_task_returns_to_pending(tmp_path) -> None:
    cfg = config("unused.sqlite")
    store = MarketDataStore(tmp_path / "market.sqlite")
    store.initialize()
    store.upsert_securities(pd.DataFrame([{
        "code": "sh.600000", "code_name": "浦发银行", "ipoDate": "1999-11-10", "outDate": "", "type": "1", "status": "1",
    }]))
    assert store.prepare_daily_tasks(cfg) == 1
    task = store.pending_tasks(cfg.retries, None)[0]
    store.mark_task_running(str(task["task_key"]))
    assert store.reset_interrupted_tasks() == 1
    assert store.pending_tasks(cfg.retries, None)[0]["status"] == "pending"


def test_claim_tasks_atomically_partitions_work(tmp_path) -> None:
    cfg = config("unused.sqlite")
    store = MarketDataStore(tmp_path / "market.sqlite")
    store.initialize()
    store.upsert_securities(pd.DataFrame([
        {"code": code, "code_name": code, "ipoDate": "2010-01-01", "outDate": "", "type": "1", "status": "1"}
        for code in ["sh.600000", "sh.600001", "sz.000001"]
    ]))
    store.prepare_daily_tasks(cfg)
    first = store.claim_tasks(cfg.retries, 2)
    second = store.claim_tasks(cfg.retries, 2)
    assert len(first) == 2
    assert len(second) == 1
    assert {task["task_key"] for task in first}.isdisjoint({task["task_key"] for task in second})
    with store.connect() as connection:
        assert connection.execute("SELECT SUM(attempts) FROM market_download_tasks").fetchone()[0] == 0


def test_daily_tasks_include_configured_benchmark(tmp_path) -> None:
    cfg = MarketDataConfig(
        experiment_id="test",
        database_path="unused.sqlite",
        start="2020-01-01",
        end="2020-12-31",
        benchmark_codes=["sh.000001"],
    )
    store = MarketDataStore(tmp_path / "market.sqlite")
    store.initialize()
    store.upsert_securities(pd.DataFrame([
        {"code": "sh.600000", "code_name": "股票", "ipoDate": "1999-01-01", "outDate": "", "type": "1", "status": "1"},
        {"code": "sh.000001", "code_name": "指数", "ipoDate": "1991-01-01", "outDate": "", "type": "2", "status": "1"},
    ]))
    assert store.prepare_daily_tasks(cfg) == 2


def test_schema_uses_wal_and_tracks_delisted_count(tmp_path) -> None:
    store = MarketDataStore(tmp_path / "market.sqlite")
    store.initialize()
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_reset_daily_data_preserves_reference_tables(tmp_path) -> None:
    cfg = config("unused.sqlite")
    store = MarketDataStore(tmp_path / "market.sqlite")
    store.initialize()
    store.upsert_calendar(pd.DataFrame([{"calendar_date": "2020-01-02", "is_trading_day": "1"}]))
    store.upsert_securities(pd.DataFrame([{
        "code": "sh.600000", "code_name": "样本", "ipoDate": "1999-01-01", "outDate": "", "type": "1", "status": "1",
    }]))
    store.prepare_daily_tasks(cfg)
    store.upsert_daily_bars(pd.DataFrame([{
        "code": "sh.600000", "trade_date": "2020-01-02", "open": 10, "high": 11, "low": 9, "close": 10.5,
        "preclose": 10, "volume": 1000, "amount": 10000, "adjustflag": 3, "turnover": 1.2,
        "trade_status": 1, "pct_change": 5, "is_st": 0, "source": "BaoStock",
    }]))
    result = store.reset_daily_data()
    status = store.status()
    assert result["deletedDailyBars"] == 1
    assert status["dailyBarCount"] == 0
    assert status["securityCount"] == 1
    assert status["calendarDays"] == 1
