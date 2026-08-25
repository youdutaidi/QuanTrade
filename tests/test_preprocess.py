import numpy as np
import pandas as pd

from qforge.preprocess import equal_composite, prepare_scores


def test_cross_sectional_scores_are_centered() -> None:
    dates = pd.bdate_range("2025-01-01", periods=2)
    raw = pd.DataFrame([[1, 2, 100], [2, 4, 6]], index=dates, columns=list("ABC"))
    scores = prepare_scores(raw, raw.notna(), 3.0)
    assert np.allclose(scores.mean(axis=1), 0)


def test_composite_averages_available_factors() -> None:
    date = pd.Timestamp("2025-01-01")
    one = pd.DataFrame([[1.0, np.nan]], index=[date], columns=["A", "B"])
    two = pd.DataFrame([[3.0, 2.0]], index=[date], columns=["A", "B"])
    result = equal_composite({"one": one, "two": two})
    assert result.loc[date, "A"] == 2.0
    assert result.loc[date, "B"] == 2.0

