from __future__ import annotations

import numpy as np
import pandas as pd

from qforge.marketdata.panel import total_return_ohlcv


def test_total_return_panel_removes_false_ex_date_crash() -> None:
    raw = pd.DataFrame([
        {"code": "sh.600000", "trade_date": "2020-01-02", "open": 10, "high": 10, "low": 10, "close": 10, "preclose": 10, "volume": 100, "amount": 1000, "turnover": 1, "trade_status": 1, "pct_change": 0, "is_st": 0},
        {"code": "sh.600000", "trade_date": "2020-01-03", "open": 9, "high": 9, "low": 9, "close": 9, "preclose": 9, "volume": 100, "amount": 900, "turnover": 1, "trade_status": 1, "pct_change": 0, "is_st": 0},
        {"code": "sh.600000", "trade_date": "2020-01-06", "open": 9, "high": 10, "low": 9, "close": 9.9, "preclose": 9, "volume": 100, "amount": 990, "turnover": 1, "trade_status": 1, "pct_change": 10, "is_st": 0},
    ])
    panel = total_return_ohlcv(raw)
    assert np.allclose(panel["close"].to_numpy(), [1.0, 1.0, 1.1])


def test_suspended_day_carries_close_but_blocks_open(tmp_path) -> None:
    raw = pd.DataFrame([
        {"code": "sh.600000", "trade_date": "2020-01-02", "open": 10, "high": 10, "low": 10, "close": 10, "preclose": 10, "volume": 100, "amount": 1000, "turnover": 1, "trade_status": 1, "pct_change": 0, "is_st": 0},
        {"code": "sh.600000", "trade_date": "2020-01-03", "open": None, "high": None, "low": None, "close": None, "preclose": 10, "volume": 0, "amount": 0, "turnover": 0, "trade_status": 0, "pct_change": None, "is_st": 0},
    ])
    panel = total_return_ohlcv(raw)
    assert panel.iloc[1]["close"] == 1.0
    assert np.isnan(panel.iloc[1]["open"])
