from __future__ import annotations

import pandas as pd

from qforge.marketdata.verify import compare_daily_frames


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
