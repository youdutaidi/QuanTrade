"""Run transparent long-only A-share price-factor candidates with explicit evidence labels."""

from __future__ import annotations

import itertools
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research/data"
OUTPUT = ROOT / "research/output"
APP_DATA = ROOT / "app/data"
EVAL_START = pd.Timestamp("2025-08-25")
DESIGN_END = pd.Timestamp("2026-02-24")
EVAL_END = pd.Timestamp("2026-08-24")
BUY_COST = 0.0015
SELL_COST = 0.0020


@dataclass(frozen=True)
class Config:
    family: str
    lookback: int
    skip: int
    rebalance: int
    top_n: int
    weighting: str
    regime: int

    @property
    def label(self) -> str:
        return f"{self.family}-L{self.lookback}-S{self.skip}-R{self.rebalance}-N{self.top_n}-{self.weighting}-M{self.regime}"


def metrics(curve: pd.Series, turnover: pd.Series) -> dict[str, float | int]:
    curve = curve.dropna()
    daily = curve.pct_change().dropna()
    drawdown = curve / curve.cummax() - 1
    years = max((curve.index[-1] - curve.index[0]).days / 365.25, 1 / 365.25)
    total = float(curve.iloc[-1] / curve.iloc[0] - 1)
    return {
        "totalReturn": total,
        "annualizedReturn": float((1 + total) ** (1 / years) - 1) if total > -1 else -1,
        "maxDrawdown": float(drawdown.min()),
        "sharpe": float(np.sqrt(252) * daily.mean() / daily.std()) if daily.std() > 0 else 0.0,
        "volatility": float(np.sqrt(252) * daily.std()) if len(daily) else 0.0,
        "turnover": float(turnover.sum()),
        "rebalanceCount": int((turnover > 1e-9).sum()),
    }


def signal_for(config: Config, close: pd.DataFrame) -> pd.DataFrame:
    if config.family == "momentum":
        return close.shift(config.skip) / close.shift(config.skip + config.lookback) - 1
    if config.family == "risk_adjusted_momentum":
        momentum = close.shift(config.skip) / close.shift(config.skip + config.lookback) - 1
        vol = close.pct_change().rolling(min(63, config.lookback)).std().shift(config.skip)
        return momentum / vol.replace(0, np.nan)
    if config.family == "breakout":
        high = close.shift(1).rolling(config.lookback).max()
        trend = close.shift(1) / close.shift(1 + min(config.lookback, 63)) - 1
        return close.shift(1) / high - 1 + trend
    if config.family == "reversal_in_trend":
        long_trend = close.shift(1) / close.shift(121) - 1
        short_reversal = -(close.shift(1) / close.shift(6) - 1)
        return short_reversal.where(long_trend > 0)
    raise ValueError(config.family)


def run(
    config: Config,
    open_px: pd.DataFrame,
    close: pd.DataFrame,
    benchmark: pd.Series,
    score: pd.DataFrame,
    liquid: pd.DataFrame,
    trend_ok: pd.DataFrame,
    vol: pd.DataFrame,
    regime_ok: pd.Series,
) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
    common = open_px.index.intersection(close.index).intersection(benchmark.index)
    open_px, close, benchmark = open_px.loc[common], close.loc[common], benchmark.loc[common]

    weights = pd.DataFrame(0.0, index=common, columns=close.columns)
    last = pd.Series(0.0, index=close.columns)
    eval_dates = common[(common >= EVAL_START) & (common <= EVAL_END)]
    for position, date in enumerate(eval_dates):
        if position % config.rebalance != 0:
            weights.loc[date] = last
            continue
        if not bool(regime_ok.loc[date]):
            last = last * 0
            weights.loc[date] = last
            continue
        available = open_px.loc[date].notna() & score.loc[date].notna() & liquid.loc[date] & trend_ok.loc[date]
        ranked = score.loc[date, available].sort_values(ascending=False).head(config.top_n)
        last = last * 0
        if len(ranked):
            if config.weighting == "inverse_vol":
                inv = 1 / vol.loc[date, ranked.index].replace(0, np.nan)
                inv = inv.replace([np.inf, -np.inf], np.nan).dropna()
                if len(inv):
                    last.loc[inv.index] = inv / inv.sum()
            else:
                last.loc[ranked.index] = 1 / len(ranked)
        weights.loc[date] = last

    weights = weights.loc[eval_dates]
    open_eval = open_px.loc[eval_dates]
    gross_returns = open_eval.shift(-1) / open_eval - 1
    gross_returns = gross_returns.replace([np.inf, -np.inf], np.nan).fillna(0)
    previous = weights.shift(1).fillna(0)
    buys = (weights - previous).clip(lower=0).sum(axis=1)
    sells = (previous - weights).clip(lower=0).sum(axis=1)
    transaction_cost = buys * BUY_COST + sells * SELL_COST
    portfolio_return = (weights * gross_returns).sum(axis=1) - transaction_cost
    portfolio_return.iloc[-1] -= weights.iloc[-1].sum() * SELL_COST
    turnover = buys + sells
    curve = (1 + portfolio_return).cumprod()
    curve.iloc[0] = max(curve.iloc[0], 1 - transaction_cost.iloc[0])
    return curve, turnover, weights


def slice_metrics(curve: pd.Series, turnover: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, float | int]:
    sub = curve.loc[(curve.index >= start) & (curve.index <= end)]
    if sub.empty:
        return {}
    normalized = sub / sub.iloc[0]
    return metrics(normalized, turnover.reindex(sub.index).fillna(0))


def main() -> None:
    market = pd.read_parquet(DATA / "csi800_ohlcv.parquet")
    members = pd.read_csv(DATA / "csi800_membership_snapshot.csv", dtype={"code": str})
    universe = sorted(set(members["symbol"]))
    market["date"] = pd.to_datetime(market["date"]).dt.tz_localize(None)
    market = market.loc[market["symbol"].isin(universe)]
    open_px = market.pivot(index="date", columns="symbol", values="open").sort_index()
    close = market.pivot(index="date", columns="symbol", values="close").sort_index()
    volume = market.pivot(index="date", columns="symbol", values="volume").sort_index()

    benchmark_frame = pd.read_parquet(DATA / "csi800_ohlcv.parquet")
    benchmark_frame["date"] = pd.to_datetime(benchmark_frame["date"]).dt.tz_localize(None)
    benchmark = benchmark_frame.loc[benchmark_frame["symbol"] == "000001.SS"].set_index("date")["close"].sort_index()

    configs = []
    for family, lookback, skip, rebalance, top_n, weighting, regime in itertools.product(
        ["momentum", "risk_adjusted_momentum", "breakout", "reversal_in_trend"],
        [20, 63, 126, 252],
        [1, 5, 20],
        [5, 10, 20],
        [1, 3, 5, 10],
        ["equal"],
        [0, 120, 200],
    ):
        if family == "reversal_in_trend" and lookback != 20:
            continue
        if family == "breakout" and skip != 1:
            continue
        configs.append(Config(family, lookback, skip, rebalance, top_n, weighting, regime))

    dollar_volume = (close * volume).rolling(20).median().shift(1)
    liquid = dollar_volume.rank(axis=1, pct=True) >= 0.30
    trend_ok = close.shift(1) > close.shift(121)
    vol = close.pct_change().rolling(63).std().shift(1)
    signal_cache: dict[tuple[str, int, int], pd.DataFrame] = {}
    regime_cache = {
        0: pd.Series(True, index=benchmark.index),
        120: benchmark.shift(1) > benchmark.shift(1).rolling(120).mean(),
        200: benchmark.shift(1) > benchmark.shift(1).rolling(200).mean(),
    }

    rows = []
    curves: dict[str, tuple[pd.Series, pd.Series]] = {}
    for index, config in enumerate(configs, 1):
        cache_key = (config.family, config.lookback, config.skip)
        if cache_key not in signal_cache:
            signal_cache[cache_key] = signal_for(config, close)
        curve, turnover, _ = run(
            config,
            open_px,
            close,
            benchmark,
            signal_cache[cache_key],
            liquid,
            trend_ok,
            vol,
            regime_cache[config.regime],
        )
        overall = metrics(curve / curve.iloc[0], turnover)
        design = slice_metrics(curve, turnover, EVAL_START, DESIGN_END)
        holdout = slice_metrics(curve, turnover, DESIGN_END + pd.Timedelta(days=1), EVAL_END)
        rows.append({"config": config.label, **overall, "designReturn": design.get("totalReturn", 0), "holdoutReturn": holdout.get("totalReturn", 0), "holdoutDrawdown": holdout.get("maxDrawdown", 0)})
        curves[config.label] = (curve, turnover)
        if index % 200 == 0:
            print(f"tested {index}/{len(configs)}")

    result = pd.DataFrame(rows).sort_values("totalReturn", ascending=False)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    APP_DATA.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT / "strategy_search.csv", index=False)

    oracle = result.iloc[0]
    design_pick = result.sort_values(["designReturn", "maxDrawdown"], ascending=[False, False]).iloc[0]
    robust_pick = result.loc[(result["designReturn"] > 0) & (result["holdoutReturn"] > 0)].sort_values(["holdoutReturn", "totalReturn"], ascending=False).iloc[0]
    selected_labels = [str(oracle["config"]), str(design_pick["config"]), str(robust_pick["config"])]
    config_map = {config.label: config for config in configs}

    benchmark_eval = benchmark.loc[(benchmark.index >= EVAL_START) & (benchmark.index <= EVAL_END)]
    benchmark_curve = benchmark_eval / benchmark_eval.iloc[0]
    benchmark_metrics = metrics(benchmark_curve, pd.Series(0.0, index=benchmark_curve.index))

    leaderboard = (close.loc[close.index <= EVAL_END].ffill().loc[EVAL_END] / close.loc[close.index >= EVAL_START].bfill().iloc[0] - 1).sort_values(ascending=False)
    names = members.drop_duplicates("symbol").set_index("symbol")["name"].to_dict()
    leaders = [{"symbol": symbol, "name": names.get(symbol, symbol), "return": float(value)} for symbol, value in leaderboard.head(10).items() if pd.notna(value)]

    strategies = []
    role_names = ["全窗搜索上界", "设计窗冠军", "双窗为正候选"]
    for role, label in zip(role_names, selected_labels):
        row = result.loc[result["config"] == label].iloc[0].to_dict()
        curve, _ = curves[label]
        config = config_map[label]
        cache_key = (config.family, config.lookback, config.skip)
        _, selected_turnover, selected_weights = run(
            config,
            open_px,
            close,
            benchmark,
            signal_cache[cache_key],
            liquid,
            trend_ok,
            vol,
            regime_cache[config.regime],
        )
        trades = []
        for date in selected_turnover.index[selected_turnover > 1e-9]:
            holdings = selected_weights.loc[date]
            holdings = holdings[holdings > 1e-9].sort_values(ascending=False)
            trades.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "turnover": round(float(selected_turnover.loc[date]), 6),
                    "holdings": [
                        {"symbol": symbol, "name": names.get(symbol, symbol), "weight": round(float(weight), 6)}
                        for symbol, weight in holdings.items()
                    ],
                }
            )
        points = [{"date": date.strftime("%Y-%m-%d"), "value": round(float(value), 6)} for date, value in curve.items()]
        strategies.append(
            {
                "role": role,
                "label": label,
                "parameters": {
                    "family": config.family,
                    "lookback": config.lookback,
                    "skip": config.skip,
                    "rebalance": config.rebalance,
                    "topN": config.top_n,
                    "weighting": config.weighting,
                    "regime": config.regime,
                },
                "metrics": {key: (float(value) if isinstance(value, (np.floating, float)) else int(value) if isinstance(value, (np.integer, int)) else value) for key, value in row.items() if key != "config"},
                "curve": points,
                "trades": trades,
            }
        )

    payload = {
        "asOf": EVAL_END.strftime("%Y-%m-%d"),
        "window": {"start": EVAL_START.strftime("%Y-%m-%d"), "designEnd": DESIGN_END.strftime("%Y-%m-%d"), "end": EVAL_END.strftime("%Y-%m-%d")},
        "universe": {"name": "当前 CSI 800 成份股快照", "count": len(universe), "survivorshipBias": True},
        "costModel": {"buy": BUY_COST, "sell": SELL_COST, "execution": "前一交易日收盘信号，下一交易日复权开盘价成交"},
        "testedStrategies": len(result),
        "benchmark": {"name": "上证综指", "metrics": benchmark_metrics, "curve": [{"date": date.strftime("%Y-%m-%d"), "value": round(float(value), 6)} for date, value in benchmark_curve.items()]},
        "strategies": strategies,
        "leaders": leaders,
        "gates": [
            {"name": "未来函数", "status": "partial", "note": "信号已滞后，成交使用次日开盘；复权因子的点时可得性仍需独立核验。"},
            {"name": "幸存者偏差", "status": "fail", "note": "当前成份股回放历史，不能作为可交易闭环。"},
            {"name": "交易成本", "status": "partial", "note": "已扣显式成本与滑点代理，尚未模拟涨跌停无法成交和最低佣金。"},
            {"name": "样本外", "status": "partial", "note": "网站分别展示设计窗与后半窗；尚无滚动多年份外推。"},
            {"name": "容量", "status": "partial", "note": "剔除成交额后 30%，尚未模拟冲击成本曲线。"},
            {"name": "实盘", "status": "fail", "note": "个人最大可承受回撤、资金用途与用钱时间仍未填写。"},
        ],
    }
    (APP_DATA / "backtest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "backtest_summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"tested": len(result), "oracle": oracle.to_dict(), "designPick": design_pick.to_dict(), "robustPick": robust_pick.to_dict(), "benchmark": benchmark_metrics}, ensure_ascii=False, indent=2, default=float))


if __name__ == "__main__":
    main()
