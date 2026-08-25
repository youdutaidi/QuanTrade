"""Create a corporate-action-safe research panel from raw BaoStock bars."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


def load_raw_daily(path: str | Path, start: str, end: str, adjustflag: int = 3) -> pd.DataFrame:
    query = """SELECT b.code,b.trade_date,b.open,b.high,b.low,b.close,b.preclose,b.volume,b.amount,
    b.turnover,b.trade_status,b.pct_change,b.is_st
    FROM daily_bars b JOIN listed_universe u ON u.trade_date=b.trade_date AND u.code=b.code
    WHERE b.trade_date BETWEEN ? AND ? AND b.adjustflag=? ORDER BY b.code,b.trade_date"""
    with sqlite3.connect(path) as connection:
        return pd.read_sql_query(query, connection, params=[start, end, adjustflag])


def total_return_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=_output_columns())
    required = {"code", "trade_date", "open", "high", "low", "close", "preclose", "volume", "amount", "trade_status", "pct_change", "is_st"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"raw daily frame missing columns: {sorted(missing)}")
    result = frame.copy().sort_values(["code", "trade_date"])
    result["date"] = pd.to_datetime(result["trade_date"])
    result["symbol"] = result["code"].astype(str)
    fallback_return = result["close"].div(result["preclose"]).sub(1)
    daily_return = pd.to_numeric(result["pct_change"], errors="coerce").div(100).fillna(fallback_return).fillna(0)
    growth = daily_return.add(1).clip(lower=0.01)
    result["close_total_return"] = growth.groupby(result["symbol"]).cumprod()
    previous_index = result["close_total_return"].div(growth)
    fallback_base = result["close"].replace(0, np.nan)
    for field in ["open", "high", "low"]:
        ratio = result[field].div(result["preclose"].replace(0, np.nan))
        ratio = ratio.fillna(result[field].div(fallback_base))
        result[f"{field}_total_return"] = previous_index.mul(ratio)
    result["close"] = result["close_total_return"]
    result["open"] = result["open_total_return"]
    result["high"] = result["high_total_return"]
    result["low"] = result["low_total_return"]
    suspended = pd.to_numeric(result["trade_status"], errors="coerce").ne(1)
    result.loc[suspended, ["open", "high", "low"]] = np.nan
    result["volume"] = pd.to_numeric(result["volume"], errors="coerce").fillna(0)
    return result[_output_columns()]


def export_research_panel(
    database_path: str | Path,
    output_path: str | Path,
    start: str,
    end: str,
    adjustflag: int = 3,
) -> dict[str, object]:
    raw = load_raw_daily(database_path, start, end, adjustflag)
    panel = total_return_ohlcv(raw)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(output, index=False)
    return {
        "output": str(output),
        "rows": len(panel),
        "symbols": int(panel["symbol"].nunique()) if len(panel) else 0,
        "firstDate": str(panel["date"].min().date()) if len(panel) else None,
        "lastDate": str(panel["date"].max().date()) if len(panel) else None,
        "bytes": output.stat().st_size,
    }


def _output_columns() -> list[str]:
    return ["date", "symbol", "open", "high", "low", "close", "volume", "amount", "turnover", "trade_status", "is_st"]
