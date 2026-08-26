from __future__ import annotations

import pandas as pd

from qforge.marketdata.verify import compare_adjustment_frames, compare_daily_frames, verify_source_sample


def frame(close: float) -> pd.DataFrame:
    return pd.DataFrame([{
        "code": "sh.600000", "trade_date": "2020-01-02", "open": 10.0, "high": 11.0, "low": 9.0,
        "close": close, "preclose": 10.0, "volume": 100.0, "amount": 1000.0, "turnover": 1.0,
        "trade_status": 1.0, "pct_change": 5.0, "is_st": 0.0, "adjustflag": 3,
    }])


def test_source_comparison_detects_numeric_change() -> None:
    assert compare_daily_frames(frame(10.5), frame(10.5))["status"] == "pass"
    mismatch = compare_daily_frames(frame(10.5), frame(10.6))
    assert mismatch["status"] == "mismatch"
    assert mismatch["numericMismatches"] == 1


def adjustments(value=1.2):
    return pd.DataFrame([{
        "code": "sh.600000", "operation_date": "2020-06-01", "fore_adjust_factor": 0.9,
        "back_adjust_factor": value, "adjust_factor": 1.02, "source": "BaoStock",
    }])


def test_adjustment_comparison_detects_value_date_and_duplicate_corruption():
    fresh = adjustments()
    assert compare_adjustment_frames(fresh, fresh)["status"] == "pass"
    assert compare_adjustment_frames(fresh, adjustments(1.3))["status"] == "mismatch"
    shifted = fresh.assign(operation_date="2020-06-02")
    assert compare_adjustment_frames(fresh, shifted)["reason"] == "keys"
    duplicate = pd.concat([fresh, fresh], ignore_index=True)
    assert compare_adjustment_frames(duplicate, duplicate)["reason"] == "duplicate_keys"
    assert compare_adjustment_frames(fresh.iloc[:0], fresh.iloc[:0])["status"] == "pass"


def test_source_replay_fails_when_bars_match_but_adjustments_differ(tmp_path, monkeypatch):
    import qforge.marketdata.verify as module
    from qforge.marketdata.config import MarketDataConfig
    from qforge.marketdata.store import MarketDataStore

    config = MarketDataConfig("test", "market.sqlite", "2020-01-01", "2020-12-31")
    store = MarketDataStore(tmp_path / config.database_path)
    store.initialize()
    store.upsert_securities(pd.DataFrame([{
        "code": "sh.600000", "code_name": "样本", "ipoDate": "1999-01-01", "outDate": "", "type": "1", "status": "1",
    }]))
    store.prepare_daily_tasks(config)
    store.finish_task(store.pending_tasks(3, None)[0]["task_key"], 2)
    store.upsert_daily_bars(frame(10.5).assign(source="BaoStock"))
    store.upsert_adjustments(adjustments(1.3))

    class Provider:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def daily_bars(self, *args): return frame(10.5)
        def adjustment_factors(self, *args): return adjustments(1.2)

    monkeypatch.setattr(module, "BaoStockMarketProvider", Provider)
    result = verify_source_sample(config, tmp_path, 20)
    assert result["sampleSize"] == 1
    assert result["results"][0]["daily"]["status"] == "pass"
    assert result["results"][0]["adjustments"]["status"] == "mismatch"
    assert result["allPass"] is False
