from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qforge.marketdata.panel import adjusted_price_ohlcv, total_return_ohlcv


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


def price_sample(pct_change=-99.5):
    return pd.DataFrame([{
        "code": "sh.600000", "trade_date": "2020-01-02", "open": 0.05, "high": 0.05,
        "low": 0.05, "close": 0.05, "preclose": 10, "volume": 100, "amount": 5,
        "turnover": 1, "trade_status": 1, "pct_change": pct_change, "is_st": 0,
    }])


def test_extreme_loss_is_preserved_not_clipped():
    panel = adjusted_price_ohlcv(price_sample())
    assert panel.iloc[0]["close"] == pytest.approx(0.005)
    assert panel.iloc[0]["raw_close"] == 0.05
    assert panel.iloc[0]["raw_preclose"] == 10


@pytest.mark.parametrize("pct_change", [-100, -101, np.inf])
def test_invalid_price_return_blocks_export(pct_change):
    with pytest.raises(ValueError, match="must not be clipped"):
        adjusted_price_ohlcv(price_sample(pct_change))


def test_missing_tradable_return_is_not_zero_filled():
    raw = price_sample(np.nan)
    raw.loc[0, ["close", "preclose"]] = np.nan
    with pytest.raises(ValueError, match="must not be clipped"):
        adjusted_price_ohlcv(raw)


def test_price_chain_is_prefix_invariant():
    raw = price_sample(0)
    future = price_sample(50)
    future.loc[0, "trade_date"] = "2020-01-03"
    pd.testing.assert_frame_equal(
        adjusted_price_ohlcv(raw).reset_index(drop=True),
        adjusted_price_ohlcv(pd.concat([raw, future], ignore_index=True)).iloc[:1].reset_index(drop=True),
    )
