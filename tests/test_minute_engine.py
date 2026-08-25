from pathlib import Path

import pandas as pd

from qforge.minute.config import MinuteConfig
from qforge.minute.engine import run_minute_backtest
from qforge.minute.store import MinuteStore


def synthetic_bars() -> pd.DataFrame:
    rows = []
    dates = pd.bdate_range("2026-08-17", periods=6)
    for day_number, date in enumerate(dates):
        for symbol_number, symbol in enumerate(["A", "B", "C"]):
            drift = (symbol_number - 1) * 0.005 + day_number * 0.0002
            for clock, step in [("09:35", 0.0), ("14:45", drift * 0.7), ("14:50", drift), ("14:55", drift * 1.05), ("15:00", drift * 1.1)]:
                price = 10 * (1 + step)
                rows.append({"symbol": symbol, "frequency": 5, "bar_time": pd.Timestamp(f"{date.date()} {clock}"), "trade_date": str(date.date()), "open": price, "high": price * 1.001, "low": price * 0.999, "close": price, "volume": 100000.0, "amount": price * 100000, "adjustflag": 3, "source": "synthetic"})
    return pd.DataFrame(rows)


def test_minute_pipeline_persists_ledger_and_reports(tmp_path: Path) -> None:
    config = MinuteConfig("minute-test", "minute.sqlite", 5, 3, "2026-08-17", "2026-08-24", ["A", "B", "C"], top_n=1, output_dir="output", app_output="app.json")
    store = MinuteStore(tmp_path / config.database_path)
    store.initialize()
    store.upsert_bars(synthetic_bars())
    payload = run_minute_backtest(config, tmp_path)
    assert payload["signalDays"] == 6
    assert payload["ledger"]["fillCount"] > 0
    assert (tmp_path / "output/report.html").exists()
    assert (tmp_path / "app.json").exists()
