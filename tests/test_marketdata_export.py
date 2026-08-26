from __future__ import annotations

import hashlib

import pandas as pd
import pyarrow.parquet as pq
import pytest

from qforge.marketdata.panel import adjusted_price_ohlcv, export_research_panel, load_raw_daily
from qforge.marketdata.store import MarketDataStore


def create_store(tmp_path, bad_second_stock=False):
    store = MarketDataStore(tmp_path / "market.sqlite")
    store.initialize()
    codes = ["sh.000001", "sh.600000", "sz.000001"]
    store.upsert_securities(pd.DataFrame([{
        "code": code, "code_name": code, "ipoDate": "1999-01-01", "outDate": "", "type": "1", "status": "1",
    } for code in codes]))
    days = ["2020-01-02", "2020-01-03"]
    store.upsert_calendar(pd.DataFrame([{"calendar_date": day, "is_trading_day": 1} for day in days]))
    store.upsert_daily_bars(pd.DataFrame([{
        "code": code, "trade_date": day, "open": 10, "high": 11, "low": 9, "close": 10.5,
        "preclose": 10, "volume": 100, "amount": 1000, "adjustflag": 3, "turnover": 1,
        "trade_status": 1, "pct_change": -100 if bad_second_stock and code == codes[1] else 5,
        "is_st": None if code == codes[0] else 0, "source": "BaoStock",
    } for code in codes for day in days]))
    return store


def test_chunked_export_matches_reference_and_persists_metadata(tmp_path):
    store = create_store(tmp_path)
    path = tmp_path / "panel.parquet"
    result = export_research_panel(store.path, path, "2020-01-01", "2020-12-31", symbols_per_chunk=1)
    reference = adjusted_price_ohlcv(load_raw_daily(store.path, "2020-01-01", "2020-12-31"))
    pd.testing.assert_frame_equal(pd.read_parquet(path), reference.reset_index(drop=True), check_dtype=False)
    assert result["rows"] == 6 and result["symbols"] == 3 and result["batches"] == 3
    assert result["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert pq.read_metadata(path).metadata[b"corporate_actions_verified"] == b"false"
    assert result["corporateActionsVerified"] is False


def test_export_failure_preserves_previous_artifact(tmp_path):
    store = create_store(tmp_path, bad_second_stock=True)
    path = tmp_path / "panel.parquet"
    path.write_bytes(b"previous artifact")
    with pytest.raises(ValueError, match="must not be clipped"):
        export_research_panel(store.path, path, "2020-01-01", "2020-12-31", symbols_per_chunk=1)
    assert path.read_bytes() == b"previous artifact"
    assert not list(tmp_path.glob(".panel.parquet-*"))


def test_empty_export_is_rejected(tmp_path):
    store = MarketDataStore(tmp_path / "market.sqlite")
    store.initialize()
    with pytest.raises(ValueError, match="empty research panel"):
        export_research_panel(store.path, tmp_path / "panel.parquet", "2020-01-01", "2020-12-31")
    assert not (tmp_path / "panel.parquet").exists()
