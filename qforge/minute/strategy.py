"""Pure completed-bar signal definitions for the minute pilot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from .config import MinuteConfig


SignalFunction = Callable[[pd.DataFrame, MinuteConfig], pd.DataFrame]


@dataclass(frozen=True)
class MinuteStrategySpec:
    name: str
    description: str
    compute: SignalFunction


def close_strength_signals(bars: pd.DataFrame, config: MinuteConfig) -> pd.DataFrame:
    cutoff = pd.to_datetime(config.signal_time).time()
    local = bars.copy().sort_values(["trade_date", "symbol", "bar_time"])
    local["next_bar_time"] = local.groupby(["trade_date", "symbol"])["bar_time"].shift(-1)
    completed = local.loc[local["bar_time"].dt.time <= cutoff]
    raw = completed.groupby(["trade_date", "symbol"], as_index=False).agg(
        signal_time=("bar_time", "last"),
        execution_time=("next_bar_time", "last"),
        first_open=("open", "first"),
        signal_close=("close", "last"),
        cumulative_volume=("volume", "sum"),
        cumulative_amount=("amount", "sum"),
    )
    raw = raw.loc[raw["execution_time"].notna() & raw["cumulative_volume"].gt(0)].copy()
    vwap = raw["cumulative_amount"] / raw["cumulative_volume"]
    raw["intraday_return"] = raw["signal_close"] / raw["first_open"] - 1
    raw["vwap_edge"] = raw["signal_close"] / vwap - 1
    return _rank_daily(raw, config.top_n)


def _rank_daily(frame: pd.DataFrame, top_n: int) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["trade_date", "symbol", "signal_time", "execution_time", "score", "target_weight"])
    parts = []
    for _, group in frame.groupby("trade_date", sort=True):
        group = group.copy()
        group["score"] = 0.7 * _zscore(group["intraday_return"]) + 0.3 * _zscore(group["vwap_edge"])
        selected = group["score"].rank(method="first", ascending=False) <= top_n
        group["target_weight"] = np.where(selected, 1 / min(top_n, len(group)), 0.0)
        parts.append(group)
    return pd.concat(parts, ignore_index=True).sort_values(["execution_time", "symbol"])


def _zscore(series: pd.Series) -> pd.Series:
    std = series.std()
    return (series - series.mean()) / std if std and not np.isnan(std) else series * 0


STRATEGIES = {
    "close_strength": MinuteStrategySpec(
        "close_strength",
        "14:50 completed-bar cross-sectional intraday return and VWAP strength; next-bar execution",
        close_strength_signals,
    )
}


def compute_signals(bars: pd.DataFrame, config: MinuteConfig) -> pd.DataFrame:
    if config.strategy not in STRATEGIES:
        raise KeyError(f"unknown minute strategy: {config.strategy}")
    return STRATEGIES[config.strategy].compute(bars, config)
