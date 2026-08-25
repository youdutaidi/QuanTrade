import numpy as np
import pandas as pd

from qforge.data import MarketPanel
from qforge.factors import compute_factor


def panel() -> MarketPanel:
    dates = pd.bdate_range("2024-01-02", periods=300)
    columns = ["A", "B"]
    close = pd.DataFrame({"A": np.arange(1, 301), "B": np.arange(301, 1, -1)}, index=dates, dtype=float)
    ones = pd.DataFrame(1.0, index=dates, columns=columns)
    return MarketPanel(close, close, close, close, ones, None)


def test_momentum_uses_only_prior_closes() -> None:
    market = panel()
    factor = compute_factor("momentum_20_5", market)
    date = market.dates[100]
    expected = market.close.loc[market.dates[95], "A"] / market.close.loc[market.dates[75], "A"] - 1
    assert factor.loc[date, "A"] == expected


def test_future_mutation_does_not_change_past_factor() -> None:
    market = panel()
    before = compute_factor("momentum_60_5", market).loc[market.dates[150]].copy()
    changed = market.close.copy()
    changed.loc[market.dates[151] :, "A"] *= 100
    mutated = MarketPanel(changed, changed, changed, changed, market.volume, None)
    after = compute_factor("momentum_60_5", mutated).loc[market.dates[150]]
    pd.testing.assert_series_equal(before, after)

