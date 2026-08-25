from pathlib import Path

import pandas as pd

from qforge.minute.broker import PaperBroker
from qforge.minute.config import MinuteConfig
from qforge.minute.store import MinuteStore


def config(path: Path) -> MinuteConfig:
    return MinuteConfig("test", str(path), 5, 3, "2026-08-21", "2026-08-24", ["A"], top_n=1, initial_cash=100000, max_participation=0.1)


def execution_bar(date: str) -> pd.DataFrame:
    return pd.DataFrame([{"symbol": "A", "bar_time": pd.Timestamp(f"{date} 14:55"), "trade_date": date, "open": 10.0, "high": 10.1, "low": 9.9, "close": 10.0, "volume": 100000.0, "amount": 1e6}])


def test_board_lot_costs_and_t_plus_one(tmp_path: Path) -> None:
    cfg = config(tmp_path / "minute.sqlite")
    store = MinuteStore(cfg.database_path)
    store.initialize()
    run_id = store.begin_strategy(cfg)
    broker = PaperBroker(cfg, store, run_id)
    broker.advance_date("2026-08-21")
    broker.rebalance(pd.Series({"A": 1.0}), execution_bar("2026-08-21"), {"A": 9.9})
    assert broker.positions["A"].quantity % 100 == 0
    assert broker.positions["A"].available_quantity == 0
    broker.rebalance(pd.Series({"A": 0.0}), execution_bar("2026-08-21"), {"A": 9.9})
    assert broker.positions["A"].quantity > 0
    broker.advance_date("2026-08-24")
    broker.rebalance(pd.Series({"A": 0.0}), execution_bar("2026-08-24"), {"A": 9.9})
    assert broker.positions["A"].quantity == 0
    summary = store.ledger_summary(run_id)
    assert summary["explicitCosts"] > 0
    assert summary["rejectedOrders"] == 1

