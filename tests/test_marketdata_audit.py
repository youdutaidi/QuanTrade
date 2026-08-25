from __future__ import annotations

import pandas as pd

from qforge.marketdata.audit import audit_market_database
from qforge.marketdata.config import MarketDataConfig
from qforge.marketdata.store import MarketDataStore


def test_audit_rejects_incomplete_download(tmp_path) -> None:
    config = MarketDataConfig(
        experiment_id="audit-test",
        database_path="market.sqlite",
        start="2020-01-01",
        end="2020-12-31",
    )
    store = MarketDataStore(tmp_path / "market.sqlite")
    store.initialize()
    store.upsert_calendar(pd.DataFrame([{"calendar_date": "2020-01-02", "is_trading_day": "1"}]))
    store.upsert_securities(pd.DataFrame([{
        "code": "sh.600000", "code_name": "样本", "ipoDate": "1999-01-01", "outDate": "", "type": "1", "status": "1",
    }]))
    store.prepare_daily_tasks(config)
    payload = audit_market_database(config, tmp_path)
    assert payload["quickCheck"] == "ok"
    assert payload["tasksComplete"] is False
    assert payload["dataReady"] is False


def test_audit_flags_invalid_tradable_bar(tmp_path) -> None:
    config = MarketDataConfig(
        experiment_id="audit-test",
        database_path="market.sqlite",
        start="2020-01-01",
        end="2020-12-31",
    )
    store = MarketDataStore(tmp_path / "market.sqlite")
    store.initialize()
    store.upsert_calendar(pd.DataFrame([{"calendar_date": "2020-01-02", "is_trading_day": "1"}]))
    store.upsert_securities(pd.DataFrame([{
        "code": "sh.600000", "code_name": "样本", "ipoDate": "1999-01-01", "outDate": "", "type": "1", "status": "1",
    }]))
    store.upsert_daily_bars(pd.DataFrame([{
        "code": "sh.600000", "trade_date": "2020-01-02", "open": 10, "high": 9, "low": 8, "close": 10,
        "preclose": 10, "volume": 100, "amount": 1000, "adjustflag": 3, "turnover": 1,
        "trade_status": 1, "pct_change": 0, "is_st": 0, "source": "BaoStock",
    }]))
    payload = audit_market_database(config, tmp_path)
    assert payload["integrity"]["invalidOhlcEnvelope"] == 1
    assert payload["integrityPass"] is False
