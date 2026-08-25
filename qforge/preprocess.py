"""Cross-sectional data cleaning that never looks forward in time."""

from __future__ import annotations

import numpy as np
import pandas as pd


def liquidity_mask(close: pd.DataFrame, volume: pd.DataFrame, floor_pct: float) -> pd.DataFrame:
    dollar_volume = (close * volume).rolling(20).median().shift(1)
    return dollar_volume.rank(axis=1, pct=True) >= floor_pct


def tradable_mask(open_px: pd.DataFrame, close: pd.DataFrame) -> pd.DataFrame:
    return open_px.notna() & close.shift(1).notna()


def winsorize_mad(frame: pd.DataFrame, scale: float) -> pd.DataFrame:
    median = frame.median(axis=1)
    deviation = frame.sub(median, axis=0).abs().median(axis=1)
    lower = median - scale * 1.4826 * deviation
    upper = median + scale * 1.4826 * deviation
    return frame.clip(lower=lower, upper=upper, axis=0)


def zscore(frame: pd.DataFrame) -> pd.DataFrame:
    mean = frame.mean(axis=1)
    std = frame.std(axis=1).replace(0, np.nan)
    return frame.sub(mean, axis=0).div(std, axis=0)


def prepare_scores(
    raw: pd.DataFrame,
    eligible: pd.DataFrame,
    winsor_scale: float,
) -> pd.DataFrame:
    aligned = raw.where(eligible)
    return zscore(winsorize_mad(aligned, winsor_scale))


def equal_composite(scores: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if not scores:
        raise ValueError("cannot build a composite without factors")
    stacked = pd.concat(scores, names=["factor", "date"])
    return stacked.groupby(level="date").mean()

