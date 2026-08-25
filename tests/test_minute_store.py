from pathlib import Path

import pandas as pd

from qforge.minute.store import MinuteStore


def one_bar(close: float = 10.0) -> pd.DataFrame:
    return pd.DataFrame([{
        "symbol": "sz.000001", "frequency": 5, "bar_time": pd.Timestamp("2026-08-24 09:35:00"),
        "trade_date": "2026-08-24", "open": 10.0, "high": 10.1, "low": 9.9, "close": close,
        "volume": 10000.0, "amount": 100000.0, "adjustflag": 3, "source": "test",
    }])


def test_schema_and_upsert_are_idempotent(tmp_path: Path) -> None:
    store = MinuteStore(tmp_path / "minute.sqlite")
    store.initialize()
    store.initialize()
    assert store.upsert_bars(one_bar()) == 1
    assert store.upsert_bars(one_bar(10.2)) == 1
    status = store.status()
    assert status["barCount"] == 1
    with store.connect() as connection:
        close = connection.execute("SELECT close FROM minute_bars").fetchone()[0]
    assert close == 10.2

