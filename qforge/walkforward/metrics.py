"""Pure period arithmetic, including initial entry costs and calendar duration."""

from __future__ import annotations

import numpy as np
import pandas as pd


def period_metrics(equity: pd.Series, initial_cash: float, start: str, end: str) -> dict:
    dates = pd.DatetimeIndex(equity.index)
    low, high = pd.Timestamp(start), pd.Timestamp(end)
    if equity.empty or not dates.is_unique or not dates.is_monotonic_increasing or low > high:
        raise ValueError("invalid equity sequence or period")
    values = equity.to_numpy(dtype=float)
    if not np.isfinite(initial_cash) or initial_cash <= 0 or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("equity and initial capital must be positive and finite")
    if dates.min() < low or dates.max() > high:
        raise ValueError("equity falls outside the declared period")
    wealth = np.r_[initial_cash, values]
    returns = wealth[1:] / wealth[:-1] - 1
    days = (high - low).days + 1
    total = values[-1] / initial_cash - 1
    std = float(returns.std(ddof=1)) if len(returns) > 1 else 0.0
    return {"totalReturn": float(total), "annualizedReturn": float((1 + total) ** (365.25 / days) - 1) if days >= 365 else None,
            "maxDrawdown": float((wealth / np.maximum.accumulate(wealth) - 1).min()),
            "sharpe": float(returns.mean() / std * np.sqrt(252)) if std > 0 else None,
            "annualizedVolatility": float(std * np.sqrt(252)), "calendarDays": days,
            "sessions": len(values), "initialEquity": initial_cash, "finalEquity": float(values[-1])}
