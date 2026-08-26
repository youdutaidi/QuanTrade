"""Causal market-residual factors; these are scores, not investable P&L."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .specification import Candidate, StudySpec


def market_residuals(returns: pd.DataFrame, market: pd.Series, lookback: int = 60) -> pd.DataFrame:
    """Subtract an intercept and beta fitted entirely before each residual day."""
    _check_alignment(returns, market)
    if lookback < 2:
        raise ValueError("OLS lookback must be at least two sessions")
    covariance = returns.rolling(lookback, min_periods=lookback).cov(market)
    variance = market.rolling(lookback, min_periods=lookback).var(ddof=1).replace(0, np.nan)
    beta = covariance.div(variance, axis=0)
    means = returns.rolling(lookback, min_periods=lookback).mean()
    market_mean = market.rolling(lookback, min_periods=lookback).mean()
    intercept = means - beta.mul(market_mean, axis=0)
    return (returns - intercept.shift(1) - beta.shift(1).mul(market, axis=0)).replace([np.inf, -np.inf], np.nan)


def candidate_scores(
    candidate: Candidate, returns: pd.DataFrame, residuals: pd.DataFrame, eligible: pd.DataFrame, spec: StudySpec,
) -> pd.DataFrame:
    _check_alignment(returns, residuals)
    _check_alignment(returns, eligible)
    if candidate.family == "fixed_equal_composite":
        settings = spec.values["signals"]["composite_windows"][candidate.window]
        parts = _composite_parts(settings, returns, residuals)
        normalized = [cross_sectional_zscore(part.where(eligible), spec.values["signals"]["mad_clip"]) for part in parts]
        # Ordinary addition requires all four components; no skip-NaN average.
        return sum(normalized) / len(normalized)
    return _single_score(candidate.family, candidate.lookback, candidate.skip, returns, residuals).where(eligible)


def cross_sectional_zscore(scores: pd.DataFrame, mad_clip: float = 5.0) -> pd.DataFrame:
    if not np.isfinite(mad_clip) or mad_clip <= 0:
        raise ValueError("MAD multiplier must be positive and finite")
    scores = scores.replace([np.inf, -np.inf], np.nan)
    median = scores.median(axis=1)
    mad = scores.sub(median, axis=0).abs().median(axis=1)
    width = (mad_clip * mad).where(mad > 0, np.inf)
    clipped = scores.clip(lower=median - width, upper=median + width, axis=0)
    mean, std = clipped.mean(axis=1), clipped.std(axis=1, ddof=1).replace(0, np.nan)
    return clipped.sub(mean, axis=0).div(std, axis=0)


def eligible_universe(
    amount: pd.DataFrame, trade_status: pd.DataFrame, is_st: pd.DataFrame, listed: pd.DataFrame, spec: StudySpec,
) -> pd.DataFrame:
    """Use observed listed sessions as a conservative lower bound on IPO age.

    `listed` must be constructed from the admitted lifecycle, security type and
    ordinary A-share prefixes, not today's constituent membership or name.
    """
    for frame in [trade_status, is_st, listed]:
        _check_alignment(amount, frame)
    if not listed.isin([True, False]).all().all():
        raise ValueError("listed mask must have an explicit boolean for every cell")
    rule = spec.values["universe"]
    liquidity = amount.shift(rule["liquidity_lag"]).rolling(rule["liquidity_lookback"]).median()
    age = listed.astype(bool).cumsum()
    return (listed & age.ge(rule["minimum_listing_sessions"]) & trade_status.eq(1)
            & is_st.eq(0) & liquidity.ge(rule["minimum_median_amount_cny"]))


def equal_weight_targets(scores: pd.Series, top_n: int, max_weight: float = 0.1) -> pd.Series:
    if top_n < 1 or 1 / top_n > max_weight:
        raise ValueError("invalid concentration")
    if not scores.index.is_unique:
        raise ValueError("duplicate symbols")
    finite = scores.replace([np.inf, -np.inf], np.nan).dropna().sort_index()
    selected = finite.sort_values(ascending=False, kind="stable").head(top_n)
    return pd.Series(1.0 / top_n, index=selected.index, dtype=float)


def _single_score(family: str, lookback: int, skip: int, returns: pd.DataFrame, residuals: pd.DataFrame) -> pd.DataFrame:
    if lookback < 2 or skip < 0:
        raise ValueError("invalid factor window")
    if family == "residual_momentum":
        history = residuals.shift(skip).rolling(lookback, min_periods=lookback)
        return history.sum().div(history.std(ddof=1).replace(0, np.nan))
    if family == "short_reversal":
        valid = returns.where(returns.gt(-1))
        return -np.expm1(np.log1p(valid).rolling(lookback, min_periods=lookback).sum())
    if family == "low_idiosyncratic_volatility":
        return -residuals.rolling(lookback, min_periods=lookback).std(ddof=1)
    if family == "low_maximum_return":
        return -returns.rolling(lookback, min_periods=lookback).max()
    raise ValueError(f"unknown factor family: {family}")


def _composite_parts(settings: dict, returns: pd.DataFrame, residuals: pd.DataFrame) -> list[pd.DataFrame]:
    return [
        _single_score("residual_momentum", settings["momentum"], settings["skip"], returns, residuals),
        _single_score("short_reversal", settings["reversal"], 0, returns, residuals),
        _single_score("low_idiosyncratic_volatility", settings["ivol"], 0, returns, residuals),
        _single_score("low_maximum_return", settings["max"], 0, returns, residuals),
    ]


def _check_alignment(frame: pd.DataFrame, other: pd.DataFrame | pd.Series) -> None:
    if not frame.index.is_unique or not frame.index.is_monotonic_increasing or not frame.columns.is_unique:
        raise ValueError("factor input dates must be sorted and axes unique")
    if not frame.index.equals(other.index) or isinstance(other, pd.DataFrame) and not frame.columns.equals(other.columns):
        raise ValueError("factor inputs are not aligned")
