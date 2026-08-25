"""One end-to-end factor experiment transaction."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .analytics import curve_metrics, factor_statistics, forward_open_returns
from .config import BacktestConfig
from .data import MarketPanel, load_panel, validate_panel
from .factors import FACTORS, compute_factor
from .portfolio import PortfolioResult, simulate_portfolio
from .preprocess import equal_composite, liquidity_mask, prepare_scores, tradable_mask
from .reporting import write_outputs


def run_experiment(config: BacktestConfig, root: str | Path = ".") -> dict[str, object]:
    base = Path(root).resolve()
    panel = load_panel(
        base / config.data_path,
        base / config.membership_path if config.membership_path else None,
        config.benchmark_symbol,
    )
    data_audit = validate_panel(panel)
    unknown = sorted(set(config.factors) - set(FACTORS))
    if unknown:
        raise ValueError(f"unknown factors: {unknown}")
    eligible = liquidity_mask(panel.close, panel.volume, config.liquidity_floor_pct) & tradable_mask(panel.open, panel.close)
    scores = _compute_scores(config, panel, eligible)
    if config.include_composite:
        scores["equal_composite"] = equal_composite(scores)
    payload = _assemble_payload(config, panel, eligible, scores, data_audit)
    payload["artifacts"] = write_outputs(
        payload,
        base / config.output_dir,
        str(base / config.app_output) if config.app_output else None,
    )
    return payload


def _compute_scores(
    config: BacktestConfig,
    panel: MarketPanel,
    eligible: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    scores: dict[str, pd.DataFrame] = {}
    for name in config.factors:
        raw = compute_factor(name, panel)
        scores[name] = prepare_scores(raw, eligible, config.winsor_mad)
    return scores


def _assemble_payload(
    config: BacktestConfig,
    panel: MarketPanel,
    eligible: pd.DataFrame,
    scores: dict[str, pd.DataFrame],
    data_audit: dict[str, object],
) -> dict[str, object]:
    forward = forward_open_returns(panel.open)
    results = [_evaluate_factor(name, frame, panel, eligible, forward, config) for name, frame in scores.items()]
    ranking = sorted((_ranking_row(item) for item in results), key=lambda row: row["totalReturn"], reverse=True)
    return {
        "engineVersion": "0.1.0",
        "experimentId": config.experiment_id,
        "generatedFrom": "local deterministic pipeline",
        "config": config.as_dict(),
        "dataAudit": data_audit,
        "factorCount": len(results),
        "factors": results,
        "ranking": ranking,
        "benchmark": _benchmark_payload(panel, config),
        "gates": _evidence_gates(config),
    }


def _evaluate_factor(
    name: str,
    scores: pd.DataFrame,
    panel: MarketPanel,
    eligible: pd.DataFrame,
    forward: pd.DataFrame,
    config: BacktestConfig,
) -> dict[str, object]:
    portfolio = simulate_portfolio(scores, panel, eligible, config)
    diagnostics = factor_statistics(scores, forward, config.quantiles)
    return {
        "name": name,
        "description": FACTORS[name].description if name in FACTORS else "等权标准化复合因子",
        "diagnostics": diagnostics,
        "portfolio": _portfolio_payload(portfolio, config),
    }


def _portfolio_payload(result: PortfolioResult, config: BacktestConfig) -> dict[str, object]:
    overall = curve_metrics(result.curve, result.turnover)
    design, holdout = {}, {}
    if config.design_end:
        split = pd.Timestamp(config.design_end)
        design = _slice_metrics(result, pd.Timestamp(config.start), split)
        holdout = _slice_metrics(result, split + pd.Timedelta(days=1), pd.Timestamp(config.end))
    return {
        "metrics": overall,
        "designMetrics": design,
        "holdoutMetrics": holdout,
        "totalCosts": float(result.costs.sum()),
        "blockedBuys": result.blocked_buys,
        "blockedSells": result.blocked_sells,
        "curve": [{"date": str(date.date()), "value": float(value)} for date, value in result.curve.items()],
        "rebalances": _rebalance_records(result),
    }


def _slice_metrics(result: PortfolioResult, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, float | int]:
    curve = result.curve.loc[(result.curve.index >= start) & (result.curve.index <= end)]
    if curve.empty:
        return {}
    normalized = curve / curve.iloc[0]
    turnover = result.turnover.reindex(curve.index).fillna(0)
    return curve_metrics(normalized, turnover)


def _rebalance_records(result: PortfolioResult) -> list[dict[str, object]]:
    rows = []
    for date in result.turnover.index[result.turnover > 1e-9]:
        holdings = result.weights.loc[date]
        holdings = holdings[holdings > 1e-6].sort_values(ascending=False)
        rows.append({
            "date": str(date.date()),
            "turnover": float(result.turnover.loc[date]),
            "holdings": [{"symbol": symbol, "weight": float(weight)} for symbol, weight in holdings.items()],
        })
    return rows


def _ranking_row(item: dict[str, object]) -> dict[str, object]:
    diagnostics = item["diagnostics"]
    metrics = item["portfolio"]["metrics"]
    return {
        "factor": item["name"],
        "meanIC": diagnostics["meanIC"],
        "icIR": diagnostics["icIR"],
        "icPositiveRate": diagnostics["icPositiveRate"],
        **metrics,
    }


def _benchmark_payload(panel: MarketPanel, config: BacktestConfig) -> dict[str, object] | None:
    if panel.benchmark is None:
        return None
    curve = panel.benchmark.loc[config.start : config.end].dropna()
    normalized = curve / curve.iloc[0]
    return {"name": panel.benchmark.name, "metrics": curve_metrics(normalized), "curve": [{"date": str(date.date()), "value": float(value)} for date, value in normalized.items()]}


def _evidence_gates(config: BacktestConfig) -> list[dict[str, str]]:
    return [
        {"name": "未来函数", "status": "partial", "note": "因子只读取前一收盘及更早数据并在次日开盘执行；复权因子的点时可得性仍需外部核验。"},
        {"name": "幸存者偏差", "status": "fail", "note": "当前配置使用当前CSI800成份股快照；必须接入历史成份区间表后才能升级证据。"},
        {"name": "交易摩擦", "status": "partial", "note": f"买卖成本为{config.buy_cost_bps:.0f}/{config.sell_cost_bps:.0f}bps，并近似模拟一字涨跌停；最低佣金与冲击函数未建模。"},
        {"name": "样本外", "status": "partial", "note": "提供设计窗/后半窗拆分，但该单年区间不等于多周期滚动样本外。"},
        {"name": "因子覆盖", "status": "partial", "note": "当前实现10个OHLCV因子和等权复合；324因子目录中财务/事件/分析师因子需点时数据适配器。"},
        {"name": "实盘", "status": "fail", "note": "没有模拟盘前向记录，也没有用户资金期限和最大回撤约束；禁止直接转为下单。"},
    ]
