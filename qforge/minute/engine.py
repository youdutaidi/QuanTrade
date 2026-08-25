"""Orchestrate BaoStock ingestion and one reproducible minute paper replay."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .broker import PaperBroker
from .config import MinuteConfig
from .provider import BaoStockProvider
from .reporting import write_minute_outputs, write_status
from .store import MinuteStore
from .strategy import STRATEGIES, compute_signals


def initialize_minute_store(config: MinuteConfig, root: str | Path = ".") -> dict[str, object]:
    base = Path(root).resolve()
    store = MinuteStore(base / config.database_path)
    store.initialize()
    payload = _status_payload(config, store.status())
    if config.app_output:
        write_status(payload, base / config.app_output)
    return payload


def download_baostock(config: MinuteConfig, root: str | Path = ".") -> dict[str, object]:
    base = Path(root).resolve()
    store = MinuteStore(base / config.database_path)
    store.initialize()
    run_id = store.begin_download(config)
    written = 0
    try:
        with BaoStockProvider() as provider:
            for symbol in config.symbols:
                written += store.upsert_bars(provider.fetch(symbol, config))
        store.finish_download(run_id, written)
    except Exception as error:
        store.finish_download(run_id, written, repr(error))
        raise
    payload = _status_payload(config, store.status())
    if config.app_output:
        write_status(payload, base / config.app_output)
    return payload


def run_minute_backtest(config: MinuteConfig, root: str | Path = ".") -> dict[str, object]:
    base = Path(root).resolve()
    store = MinuteStore(base / config.database_path)
    store.initialize()
    bars = store.load_bars(config)
    if bars.empty:
        raise ValueError("no minute bars found; run the minute download command first")
    signals = compute_signals(bars, config)
    if signals.empty:
        raise ValueError("minute strategy produced no executable signals")
    run_id = store.begin_strategy(config)
    try:
        _replay(signals, bars, config, store, run_id)
        store.finish_strategy(run_id)
    except Exception as error:
        store.finish_strategy(run_id, repr(error))
        raise
    payload = _result_payload(config, store, bars, signals, run_id)
    payload["artifacts"] = write_minute_outputs(payload, base / config.output_dir, str(base / config.app_output) if config.app_output else None)
    return payload


def _replay(
    signals: pd.DataFrame,
    bars: pd.DataFrame,
    config: MinuteConfig,
    store: MinuteStore,
    run_id: str,
) -> None:
    broker = PaperBroker(config, store, run_id)
    daily_last = bars.sort_values("bar_time").groupby(["trade_date", "symbol"], as_index=False).tail(1)
    daily_close = daily_last.pivot(index="trade_date", columns="symbol", values="close").sort_index()
    previous_close = daily_close.shift(1)
    for trade_date, group in signals.groupby("trade_date", sort=True):
        execution = _execution_bars(bars, group)
        if execution.empty:
            continue
        broker.advance_date(trade_date)
        store.write_signals(run_id, group)
        previous = previous_close.loc[trade_date].dropna().to_dict() if trade_date in previous_close.index else {}
        targets = group.set_index("symbol")["target_weight"]
        broker.rebalance(targets, execution, previous)
        end_rows = daily_last.loc[daily_last["trade_date"] == trade_date]
        prices = end_rows.set_index("symbol")["close"].to_dict()
        store.write_snapshot(run_id, end_rows["bar_time"].max(), broker, prices)


def _execution_bars(bars: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
    keys = signals[["symbol", "execution_time"]].rename(columns={"execution_time": "bar_time"})
    return bars.merge(keys, on=["symbol", "bar_time"], how="inner").drop_duplicates(["symbol", "bar_time"])


def _result_payload(
    config: MinuteConfig,
    store: MinuteStore,
    bars: pd.DataFrame,
    signals: pd.DataFrame,
    run_id: str,
) -> dict[str, object]:
    equity = store.load_equity(run_id)
    metrics = _equity_metrics(equity, config)
    ledger = store.ledger_summary(run_id)
    database = store.status()
    return {
        "state": "candidate_evidence",
        "experimentId": config.experiment_id,
        "runId": run_id,
        "strategy": {"name": config.strategy, "description": STRATEGIES[config.strategy].description},
        "window": {"start": config.start, "designEnd": config.design_end, "end": config.end},
        "database": database,
        "metrics": metrics,
        "ledger": ledger,
        "benchmark": _pilot_benchmark(bars, config),
        "signalDays": int(signals["trade_date"].nunique()),
        "recentOrders": store.recent_orders(run_id),
        "equity": [{"date": str(row.bar_time.date()), "value": float(row.equity / config.initial_cash)} for row in equity.itertuples()],
        "rules": _rules(config),
        "gates": _gates(),
    }


def _equity_metrics(equity: pd.DataFrame, config: MinuteConfig) -> dict[str, object]:
    values = equity.set_index("bar_time")["equity"]
    returns = values.pct_change().dropna()
    total = float(values.iloc[-1] / config.initial_cash - 1)
    max_drawdown = float(equity["drawdown"].min())
    sharpe = float(returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 1 and returns.std() > 0 else 0.0
    design, holdout = 0.0, 0.0
    if config.design_end:
        split = pd.Timestamp(config.design_end)
        design_values = values.loc[values.index <= split]
        holdout_values = values.loc[values.index > split]
        design = float(design_values.iloc[-1] / config.initial_cash - 1) if len(design_values) else 0.0
        holdout = float(holdout_values.iloc[-1] / holdout_values.iloc[0] - 1) if len(holdout_values) > 1 else 0.0
    return {"totalReturn": total, "maxDrawdown": max_drawdown, "sharpe": sharpe, "designReturn": design, "holdoutReturn": holdout, "finalEquity": float(values.iloc[-1])}


def _pilot_benchmark(bars: pd.DataFrame, config: MinuteConfig) -> dict[str, object]:
    closes = bars.sort_values("bar_time").groupby("symbol")["close"]
    returns = closes.last() / closes.first() - 1
    return {"name": "试点股票等权买入持有", "totalReturn": float(returns.mean()), "symbolReturns": {key: float(value) for key, value in returns.items()}}


def _status_payload(config: MinuteConfig, status: dict[str, object]) -> dict[str, object]:
    return {"state": "database_ready", "experimentId": config.experiment_id, "database": status, "metrics": {}, "recentOrders": [], "rules": _rules(config), "gates": _gates()}


def _rules(config: MinuteConfig) -> list[str]:
    return [
        f"{config.frequency}分钟已完成K线产生信号，下一根K线开盘模拟成交",
        f"A股T+1与{config.lot_size}股整数手",
        f"佣金{config.commission_rate*10000:.1f}bps且最低{config.minimum_commission:.0f}元，卖出印花税{config.stamp_duty_rate*10000:.1f}bps",
        f"滑点{config.slippage_bps:.1f}bps，单根K线最多参与成交量{config.max_participation:.0%}",
    ]


def _gates() -> list[dict[str, str]]:
    return [
        {"name": "未来函数", "status": "partial", "note": "信号仅使用14:50及以前完成K线，按下一根K线开盘成交；供应商复权时点仍需核验。"},
        {"name": "交易规则", "status": "partial", "note": "已实现T+1、整数手、最低佣金、印花税、参与率和一字板拒单；未覆盖全部板块/ST/除权价格限制。"},
        {"name": "盘口真实性", "status": "fail", "note": "5分钟OHLCV没有买卖盘、排队位置和逐笔成交，不能证明实际可成交。"},
        {"name": "数据覆盖", "status": "partial", "note": "固定10股试点用于打通链路，尚不是全市场或历史成份点时股票池。"},
        {"name": "前向模拟", "status": "fail", "note": "当前是历史回放，没有形成连续的未来日期模拟盘记录。"},
        {"name": "实盘连接", "status": "fail", "note": "券商接口被明确禁用；订单只写入本地SQLite。"},
    ]
