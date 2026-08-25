import pandas as pd

from qforge.portfolio import apply_execution_locks, desired_weights


def test_top_fraction_is_equal_weighted() -> None:
    scores = pd.Series({"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0})
    target = desired_weights(scores, 0.5)
    assert target.to_dict() == {"A": 0.5, "B": 0.5, "C": 0.0, "D": 0.0}


def test_limit_locks_block_buys_and_sells() -> None:
    current = pd.Series({"A": 0.5, "B": 0.5, "C": 0.0})
    desired = pd.Series({"A": 0.0, "B": 0.5, "C": 0.5})
    locked_up = pd.Series({"A": False, "B": False, "C": True})
    locked_down = pd.Series({"A": True, "B": False, "C": False})
    target, blocked_buys, blocked_sells = apply_execution_locks(desired, current, locked_up, locked_down)
    assert target["A"] == 0.5
    assert target["C"] == 0.0
    assert (blocked_buys, blocked_sells) == (1, 1)

