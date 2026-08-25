"""Factor diagnostics: IC, coverage, quantile returns and performance metrics."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def forward_open_returns(open_px: pd.DataFrame) -> pd.DataFrame:
    returns = open_px.shift(-1) / open_px - 1
    return returns.replace([np.inf, -np.inf], np.nan)


def daily_spearman_ic(scores: pd.DataFrame, forward: pd.DataFrame) -> pd.Series:
    common = scores.index.intersection(forward.index)
    values: dict[pd.Timestamp, float] = {}
    for date in common:
        pair = pd.concat([scores.loc[date], forward.loc[date]], axis=1).dropna()
        values[date] = pair.iloc[:, 0].corr(pair.iloc[:, 1], method="spearman") if len(pair) >= 5 else np.nan
    return pd.Series(values, dtype=float, name="ic")


def quantile_returns(scores: pd.DataFrame, forward: pd.DataFrame, quantiles: int) -> pd.DataFrame:
    common = scores.index.intersection(forward.index)
    rows: list[dict[str, object]] = []
    for date in common:
        pair = pd.concat([scores.loc[date], forward.loc[date]], axis=1, keys=["score", "return"]).dropna()
        if len(pair) < quantiles * 2:
            continue
        ranks = pair["score"].rank(method="first", pct=True)
        groups = np.minimum((ranks * quantiles).apply(math.ceil), quantiles).astype(int)
        means = pair["return"].groupby(groups).mean()
        rows.append({"date": date, **{f"Q{q}": means.get(q, np.nan) for q in range(1, quantiles + 1)}})
    if not rows:
        return pd.DataFrame(columns=[f"Q{q}" for q in range(1, quantiles + 1)])
    return pd.DataFrame(rows).set_index("date").sort_index()


def curve_metrics(curve: pd.Series, turnover: pd.Series | None = None) -> dict[str, float | int]:
    clean = curve.dropna()
    if len(clean) < 2:
        return _empty_metrics()
    daily = clean.pct_change().dropna()
    drawdown = clean / clean.cummax() - 1
    total = float(clean.iloc[-1] / clean.iloc[0] - 1)
    years = max((clean.index[-1] - clean.index[0]).days / 365.25, 1 / 365.25)
    volatility = float(daily.std() * np.sqrt(252)) if len(daily) else 0.0
    sharpe = float(daily.mean() / daily.std() * np.sqrt(252)) if daily.std() > 0 else 0.0
    return {
        "totalReturn": total,
        "annualizedReturn": float((1 + total) ** (1 / years) - 1) if total > -1 else -1.0,
        "maxDrawdown": float(drawdown.min()),
        "sharpe": sharpe,
        "volatility": volatility,
        "turnover": float(turnover.sum()) if turnover is not None else 0.0,
        "observations": len(clean),
    }


def factor_statistics(scores: pd.DataFrame, forward: pd.DataFrame, quantiles: int) -> dict[str, object]:
    ic = daily_spearman_ic(scores, forward).dropna()
    q_returns = quantile_returns(scores, forward, quantiles)
    q_curves = (1 + q_returns.fillna(0)).cumprod()
    spread = q_returns.get(f"Q{quantiles}", pd.Series(dtype=float)) - q_returns.get("Q1", pd.Series(dtype=float))
    return {
        "meanIC": float(ic.mean()) if len(ic) else 0.0,
        "icIR": float(ic.mean() / ic.std() * np.sqrt(252)) if len(ic) > 1 and ic.std() > 0 else 0.0,
        "icPositiveRate": float((ic > 0).mean()) if len(ic) else 0.0,
        "coverage": float(scores.notna().mean(axis=1).mean()),
        "icObservations": len(ic),
        "quantileCurves": _series_frame_records(q_curves),
        "longShortCurve": _series_records((1 + spread.fillna(0)).cumprod()),
    }


def _empty_metrics() -> dict[str, float | int]:
    return {"totalReturn": 0.0, "annualizedReturn": 0.0, "maxDrawdown": 0.0, "sharpe": 0.0, "volatility": 0.0, "turnover": 0.0, "observations": 0}


def _series_records(series: pd.Series) -> list[dict[str, object]]:
    return [{"date": str(index.date()), "value": float(value)} for index, value in series.dropna().items()]


def _series_frame_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return [{"date": str(index.date()), **{key: float(value) for key, value in row.dropna().items()}} for index, row in frame.iterrows()]
