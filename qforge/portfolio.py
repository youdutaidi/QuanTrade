"""Long-only next-open portfolio simulator with explicit frictions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import BacktestConfig
from .data import MarketPanel


@dataclass(frozen=True)
class PortfolioResult:
    curve: pd.Series
    returns: pd.Series
    turnover: pd.Series
    costs: pd.Series
    weights: pd.DataFrame
    blocked_buys: int
    blocked_sells: int


def market_regime(panel: MarketPanel, days: int) -> pd.Series:
    if days <= 0 or panel.benchmark is None:
        return pd.Series(True, index=panel.dates)
    benchmark = panel.benchmark.reindex(panel.dates).ffill()
    return benchmark.shift(1) > benchmark.shift(1).rolling(days).mean()


def locked_limits(panel: MarketPanel, threshold: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    previous_close = panel.close.shift(1)
    gap = panel.open / previous_close - 1
    one_price = panel.high.eq(panel.low) & panel.open.eq(panel.high)
    return one_price & gap.ge(threshold), one_price & gap.le(-threshold)


def desired_weights(scores: pd.Series, fraction: float) -> pd.Series:
    clean = scores.dropna().sort_values(ascending=False)
    count = max(1, int(np.ceil(len(clean) * fraction))) if len(clean) else 0
    selected = clean.head(count)
    target = pd.Series(0.0, index=scores.index)
    if len(selected):
        target.loc[selected.index] = 1 / len(selected)
    return target


def apply_execution_locks(
    desired: pd.Series,
    current: pd.Series,
    locked_up: pd.Series,
    locked_down: pd.Series,
) -> tuple[pd.Series, int, int]:
    blocked_sell = locked_down & current.gt(desired)
    blocked_buy = locked_up & desired.gt(current)
    fixed = current.where(blocked_sell, 0.0)
    flexible = desired.where(~blocked_buy & ~blocked_sell, 0.0)
    capacity = max(0.0, 1.0 - float(fixed.sum()))
    if flexible.sum() > capacity and flexible.sum() > 0:
        flexible *= capacity / flexible.sum()
    target = fixed.add(flexible, fill_value=0).clip(lower=0)
    return target, int(blocked_buy.sum()), int(blocked_sell.sum())


def simulate_portfolio(
    scores: pd.DataFrame,
    panel: MarketPanel,
    eligible: pd.DataFrame,
    config: BacktestConfig,
) -> PortfolioResult:
    dates = _evaluation_dates(scores, panel, config)
    asset_returns = panel.open.shift(-1).div(panel.open).sub(1).replace([np.inf, -np.inf], np.nan).fillna(0)
    regime = market_regime(panel, config.market_regime_days).reindex(dates).fillna(False)
    locked_up, locked_down = locked_limits(panel, config.limit_pct)
    current = pd.Series(0.0, index=panel.symbols)
    records: list[dict[str, object]] = []
    weight_rows: list[pd.Series] = []
    blocked_buys = blocked_sells = 0
    for position, date in enumerate(dates):
        rebalance = position % config.rebalance_days == 0
        if rebalance:
            available = eligible.loc[date] & panel.open.loc[date].notna()
            desired = desired_weights(scores.loc[date].where(available), config.top_quantile) if regime.loc[date] else current * 0
            if config.simulate_locked_limits:
                desired, buys_blocked, sells_blocked = apply_execution_locks(desired, current, locked_up.loc[date], locked_down.loc[date])
                blocked_buys += buys_blocked
                blocked_sells += sells_blocked
        else:
            desired = current.copy()
        current, record = _one_day(date, desired, current, asset_returns.loc[date], config)
        records.append(record)
        weight_rows.append(desired.rename(date))
    return _build_result(records, weight_rows, blocked_buys, blocked_sells, config)


def _evaluation_dates(scores: pd.DataFrame, panel: MarketPanel, config: BacktestConfig) -> pd.DatetimeIndex:
    common = scores.index.intersection(panel.open.index)
    return common[(common >= pd.Timestamp(config.start)) & (common <= pd.Timestamp(config.end))]


def _one_day(
    date: pd.Timestamp,
    target: pd.Series,
    current: pd.Series,
    asset_return: pd.Series,
    config: BacktestConfig,
) -> tuple[pd.Series, dict[str, object]]:
    delta = target - current
    buys = float(delta.clip(lower=0).sum())
    sells = float((-delta.clip(upper=0)).sum())
    cost = buys * config.buy_cost_bps / 10_000 + sells * config.sell_cost_bps / 10_000
    gross = float((target * asset_return).sum())
    net = gross - cost
    denominator = max(1 + gross, 1e-12)
    drifted = target.mul(1 + asset_return).div(denominator).fillna(0)
    record = {"date": date, "return": net, "turnover": buys + sells, "cost": cost}
    return drifted, record


def _build_result(
    records: list[dict[str, object]],
    weights: list[pd.Series],
    blocked_buys: int,
    blocked_sells: int,
    config: BacktestConfig,
) -> PortfolioResult:
    daily = pd.DataFrame(records).set_index("date")
    if len(daily):
        liquidation = pd.DataFrame(weights).iloc[-1].sum() * config.sell_cost_bps / 10_000
        daily.iloc[-1, daily.columns.get_loc("return")] -= liquidation
        daily.iloc[-1, daily.columns.get_loc("cost")] += liquidation
    curve = (1 + daily["return"]).cumprod()
    curve.name = "equity"
    return PortfolioResult(curve, daily["return"], daily["turnover"], daily["cost"], pd.DataFrame(weights), blocked_buys, blocked_sells)
