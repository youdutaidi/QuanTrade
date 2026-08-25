"""Pure OHLCV factor definitions and the public factor registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from .data import MarketPanel


FactorFunction = Callable[[MarketPanel], pd.DataFrame]


@dataclass(frozen=True)
class FactorSpec:
    name: str
    description: str
    direction: int
    minimum_history: int
    compute: FactorFunction


def _momentum(panel: MarketPanel, lookback: int, skip: int) -> pd.DataFrame:
    return panel.close.shift(skip) / panel.close.shift(skip + lookback) - 1


def _reversal(panel: MarketPanel, lookback: int) -> pd.DataFrame:
    return -(panel.close.shift(1) / panel.close.shift(1 + lookback) - 1)


def _low_volatility(panel: MarketPanel, lookback: int) -> pd.DataFrame:
    returns = panel.close.pct_change(fill_method=None)
    return -returns.rolling(lookback).std().shift(1)


def _max_return(panel: MarketPanel, lookback: int) -> pd.DataFrame:
    returns = panel.close.pct_change(fill_method=None)
    return -returns.rolling(lookback).max().shift(1)


def _amihud(panel: MarketPanel, lookback: int) -> pd.DataFrame:
    returns = panel.close.pct_change(fill_method=None).abs()
    dollar_volume = panel.close * panel.volume
    illiquidity = returns / dollar_volume.replace(0, np.nan)
    return -np.log1p(illiquidity.rolling(lookback).mean().shift(1) * 1e9)


def _volume_trend(panel: MarketPanel, lookback: int) -> pd.DataFrame:
    recent = panel.volume.shift(1).rolling(lookback).mean()
    baseline = panel.volume.shift(1 + lookback).rolling(lookback).mean()
    return np.log(recent.replace(0, np.nan) / baseline.replace(0, np.nan))


def _breakout(panel: MarketPanel, lookback: int) -> pd.DataFrame:
    past_high = panel.high.shift(1).rolling(lookback).max()
    return panel.close.shift(1) / past_high - 1


def _price_to_ma(panel: MarketPanel, lookback: int) -> pd.DataFrame:
    average = panel.close.shift(1).rolling(lookback).mean()
    return panel.close.shift(1) / average - 1


def _spec(
    name: str,
    description: str,
    direction: int,
    history: int,
    function: FactorFunction,
) -> FactorSpec:
    return FactorSpec(name, description, direction, history, function)


FACTORS: dict[str, FactorSpec] = {
    "momentum_20_5": _spec("momentum_20_5", "20日动量，跳过最近5日", 1, 26, lambda p: _momentum(p, 20, 5)),
    "momentum_60_5": _spec("momentum_60_5", "60日动量，跳过最近5日", 1, 66, lambda p: _momentum(p, 60, 5)),
    "momentum_252_21": _spec("momentum_252_21", "12-1月动量", 1, 274, lambda p: _momentum(p, 252, 21)),
    "reversal_5": _spec("reversal_5", "5日短期反转", 1, 7, lambda p: _reversal(p, 5)),
    "low_volatility_20": _spec("low_volatility_20", "20日低波动", 1, 22, lambda p: _low_volatility(p, 20)),
    "max_return_20": _spec("max_return_20", "低极端单日收益偏好", 1, 22, lambda p: _max_return(p, 20)),
    "amihud_20": _spec("amihud_20", "20日Amihud流动性代理", 1, 22, lambda p: _amihud(p, 20)),
    "volume_trend_20": _spec("volume_trend_20", "短长成交量趋势", 1, 42, lambda p: _volume_trend(p, 20)),
    "breakout_252": _spec("breakout_252", "距252日高点", 1, 253, lambda p: _breakout(p, 252)),
    "price_to_ma_120": _spec("price_to_ma_120", "价格相对120日均线", 1, 121, lambda p: _price_to_ma(p, 120)),
}


def compute_factor(name: str, panel: MarketPanel) -> pd.DataFrame:
    if name not in FACTORS:
        raise KeyError(f"unknown factor {name!r}; available={sorted(FACTORS)}")
    spec = FACTORS[name]
    values = spec.compute(panel) * spec.direction
    return values.replace([np.inf, -np.inf], np.nan)


def factor_catalog() -> list[dict[str, object]]:
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "direction": spec.direction,
            "minimumHistory": spec.minimum_history,
        }
        for spec in FACTORS.values()
    ]
