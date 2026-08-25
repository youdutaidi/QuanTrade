"""Deterministic synthetic panel for a zero-network smoke test."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def create_demo(root: str | Path, seed: int = 7) -> Path:
    base = Path(root).resolve() / "research/demo"
    base.mkdir(parents=True, exist_ok=True)
    market, symbols, dates = _synthetic_market(seed)
    market.to_parquet(base / "market.parquet", index=False)
    pd.DataFrame({"symbol": symbols, "name": symbols}).to_csv(base / "membership.csv", index=False)
    config = _demo_config(dates)
    path = base / "config.json"
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _synthetic_market(seed: int) -> tuple[pd.DataFrame, list[str], pd.DatetimeIndex]:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-02", periods=430)
    symbols = [f"DEMO{i:03d}" for i in range(40)]
    quality = np.linspace(-0.00035, 0.00035, len(symbols))
    market = rng.normal(0.0002, 0.008, (len(dates), 1))
    noise = rng.normal(0, 0.015, (len(dates), len(symbols)))
    returns = market + quality + noise
    close = 100 * np.exp(np.cumsum(returns, axis=0))
    overnight = rng.normal(0, 0.002, close.shape)
    open_px = close * np.exp(overnight)
    volume = rng.lognormal(15, 0.45, close.shape)
    frame = _long_frame(dates, symbols, open_px, close, volume)
    benchmark = _benchmark_frame(dates, market[:, 0])
    return pd.concat([frame, benchmark], ignore_index=True), symbols, dates


def _long_frame(
    dates: pd.DatetimeIndex,
    symbols: list[str],
    open_px: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
) -> pd.DataFrame:
    rows = []
    for column, symbol in enumerate(symbols):
        high = np.maximum(open_px[:, column], close[:, column]) * 1.006
        low = np.minimum(open_px[:, column], close[:, column]) * 0.994
        rows.append(pd.DataFrame({"date": dates, "symbol": symbol, "open": open_px[:, column], "high": high, "low": low, "close": close[:, column], "volume": volume[:, column]}))
    return pd.concat(rows, ignore_index=True)


def _benchmark_frame(dates: pd.DatetimeIndex, returns: np.ndarray) -> pd.DataFrame:
    close = 100 * np.exp(np.cumsum(returns))
    return pd.DataFrame({"date": dates, "symbol": "DEMO.IDX", "open": close, "high": close * 1.002, "low": close * 0.998, "close": close, "volume": 1e9})


def _demo_config(dates: pd.DatetimeIndex) -> dict[str, object]:
    return {
        "experiment_id": "QF-DEMO-01",
        "data_path": "research/demo/market.parquet",
        "membership_path": "research/demo/membership.csv",
        "benchmark_symbol": "DEMO.IDX",
        "start": str(dates[280].date()),
        "end": str(dates[-2].date()),
        "design_end": str(dates[355].date()),
        "factors": ["momentum_20_5", "momentum_60_5", "reversal_5", "low_volatility_20", "volume_trend_20"],
        "include_composite": True,
        "rebalance_days": 5,
        "top_quantile": 0.1,
        "quantiles": 5,
        "liquidity_floor_pct": 0.1,
        "market_regime_days": 0,
        "simulate_locked_limits": True,
        "output_dir": "research/demo/output",
    }

