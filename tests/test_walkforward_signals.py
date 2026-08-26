from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from qforge.walkforward.signals import candidate_scores, cross_sectional_zscore, eligible_universe, equal_weight_targets, market_residuals
from qforge.walkforward.specification import Candidate, StudySpec


@pytest.fixture
def inputs():
    rng = np.random.default_rng(42)
    index = pd.bdate_range("2020-01-01", periods=410)
    market = pd.Series(rng.normal(0, 0.01, len(index)), index=index)
    returns = pd.DataFrame(rng.normal(0, 0.02, (len(index), 12)), index=index, columns=[f"s{i:02}" for i in range(12)])
    returns = returns.add(market * 0.8, axis=0)
    spec = StudySpec.from_json(Path(__file__).resolve().parents[1] / "configs" / "walk_forward.json")
    return returns, market, spec


def test_residual_ols_is_lagged_and_removes_known_intercept_beta():
    index = pd.bdate_range("2020-01-01", periods=90)
    market = pd.Series(np.sin(np.arange(90)) * 0.02, index=index)
    returns = (market * 1.7 + 0.002).to_frame("stock")
    residuals = market_residuals(returns, market, 20)
    assert residuals.iloc[:20].isna().all().all()
    np.testing.assert_allclose(residuals.iloc[20:], 0, atol=1e-12)
    returns.iloc[30, 0] += 0.3
    assert market_residuals(returns, market, 20).iloc[30, 0] == pytest.approx(0.3)


def test_every_frozen_signal_is_prefix_invariant(inputs):
    returns, market, spec = inputs
    cut = 390
    eligible = returns.notna()
    full = market_residuals(returns, market)
    short = market_residuals(returns.iloc[:cut], market.iloc[:cut])
    assert_frame_equal(full.iloc[:cut], short)
    seen = set()
    for candidate in spec.candidates():
        key = candidate.family, candidate.lookback, candidate.skip, candidate.window
        if key in seen:
            continue
        seen.add(key)
        a = candidate_scores(candidate, returns, full, eligible, spec)
        b = candidate_scores(candidate, returns.iloc[:cut], short, eligible.iloc[:cut], spec)
        assert_frame_equal(a.iloc[:cut], b)
        assert a.iloc[-1].notna().all()
    assert len(seen) == 16


def test_reversal_uses_compounded_not_summed_returns(inputs):
    _, _, spec = inputs
    returns = pd.DataFrame({"a": [0.1, -0.1, 0.2]})
    score = candidate_scores(Candidate("short_reversal", 5, 10, 2), returns, returns, returns.notna(), spec)
    assert score.iloc[1, 0] == pytest.approx(0.01)


def test_liquidity_is_lagged_and_missing_st_excluded(inputs):
    returns, _, spec = inputs
    amount = returns * 0 + 20000000.0
    status, st, listed = amount * 0 + 1, amount * 0, amount.notna()
    amount.iloc[119, 0] = 0
    st.iloc[120, 1] = np.nan
    eligible = eligible_universe(amount, status, st, listed, spec)
    assert not eligible.iloc[:119].any().any()
    assert eligible.iloc[119].all()  # Today's amount is not used for today's eligibility.
    assert not eligible.iloc[120, 1]
    amount.iloc[120:] = 1e15
    changed = eligible_universe(amount, status, st, listed, spec)
    assert_frame_equal(eligible.iloc[:121], changed.iloc[:121])


def test_zero_dispersion_missing_components_and_deterministic_ties(inputs):
    returns, market, spec = inputs
    assert cross_sectional_zscore(pd.DataFrame([[1, 1, 1]])).isna().all().all()
    score = pd.Series([2.0, 2.0, 3.0], index=["z", "a", "b"])
    targets = equal_weight_targets(score, 10)
    assert list(targets.index) == ["b", "a", "z"]
    assert targets.sum() == pytest.approx(0.3)  # Unfilled seven slots stay cash.
    eligible = returns.notna()
    eligible.iloc[-1, 0] = False
    candidate = Candidate("fixed_equal_composite", 5, 10, window="short")
    scores = candidate_scores(candidate, returns, market_residuals(returns, market), eligible, spec)
    assert np.isnan(scores.iloc[-1, 0])


def test_unknown_listing_mask_cannot_silently_age_a_stock(inputs):
    returns, _, spec = inputs
    amount = returns * 0 + 20000000.0
    listed = amount * 0 + 1
    listed.iloc[0, 0] = np.nan
    with pytest.raises(ValueError, match="explicit boolean"):
        eligible_universe(amount, amount * 0 + 1, amount * 0, listed, spec)
