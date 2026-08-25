import pandas as pd

from qforge.minute.config import MinuteConfig
from qforge.minute.strategy import compute_signals


def config() -> MinuteConfig:
    return MinuteConfig("test", "minute.sqlite", 5, 3, "2026-08-24", "2026-08-24", ["A", "B", "C"], top_n=1)


def bars() -> pd.DataFrame:
    rows = []
    for symbol, strength in [("A", 0.03), ("B", 0.01), ("C", -0.01)]:
        for time, fraction in [("09:35", 0.0), ("14:50", strength), ("14:55", strength + 0.01)]:
            price = 10 * (1 + fraction)
            rows.append({"trade_date": pd.Timestamp("2026-08-24").date(), "symbol": symbol, "bar_time": pd.Timestamp(f"2026-08-24 {time}"), "open": price, "high": price, "low": price, "close": price, "volume": 1000.0, "amount": price * 1000})
    return pd.DataFrame(rows)


def test_future_bar_mutation_does_not_change_signal() -> None:
    frame = bars()
    before = compute_signals(frame, config()).set_index("symbol")["score"]
    frame.loc[frame["bar_time"].dt.time > pd.Timestamp("14:50").time(), "close"] *= 100
    after = compute_signals(frame, config()).set_index("symbol")["score"]
    pd.testing.assert_series_equal(before, after)

