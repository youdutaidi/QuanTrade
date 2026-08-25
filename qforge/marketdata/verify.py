"""Fresh-source sample replay for detecting silent ingestion corruption."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from .config import MarketDataConfig
from .provider import BaoStockMarketProvider


NUMERIC_FIELDS = ["open", "high", "low", "close", "preclose", "volume", "amount", "turnover", "trade_status", "pct_change", "is_st"]


def verify_source_sample(
    config: MarketDataConfig,
    root: Path,
    sample_size: int = 20,
) -> dict[str, object]:
    path = root / config.database_path
    codes = _sample_codes(path, sample_size)
    results = []
    with BaoStockMarketProvider(timeout_seconds=config.request_timeout_seconds) as provider:
        for code in codes:
            fresh = provider.daily_bars(code, config.start, config.end, config.adjustflag)
            stored = _stored_bars(path, code, config)
            result = compare_daily_frames(fresh, stored)
            results.append({"code": code, **result})
    return {
        "sampleSize": len(codes),
        "allPass": bool(results) and all(item["status"] == "pass" for item in results),
        "results": results,
    }


def compare_daily_frames(fresh: pd.DataFrame, stored: pd.DataFrame) -> dict[str, object]:
    fields = ["code", "trade_date", *NUMERIC_FIELDS, "adjustflag"]
    left = fresh[fields].sort_values(["code", "trade_date"]).reset_index(drop=True)
    right = stored[fields].sort_values(["code", "trade_date"]).reset_index(drop=True)
    if len(left) != len(right):
        return {"status": "mismatch", "freshRows": len(left), "storedRows": len(right), "reason": "row_count"}
    if not left[["code", "trade_date", "adjustflag"]].equals(right[["code", "trade_date", "adjustflag"]]):
        return {"status": "mismatch", "freshRows": len(left), "storedRows": len(right), "reason": "keys"}
    mismatches = 0
    for field in NUMERIC_FIELDS:
        a = pd.to_numeric(left[field], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(right[field], errors="coerce").to_numpy(dtype=float)
        mismatches += int((~np.isclose(a, b, rtol=1e-10, atol=1e-10, equal_nan=True)).sum())
    return {
        "status": "pass" if mismatches == 0 else "mismatch",
        "freshRows": len(left),
        "storedRows": len(right),
        "numericMismatches": mismatches,
    }


def _sample_codes(path: Path, sample_size: int) -> list[str]:
    with sqlite3.connect(path) as connection:
        codes = [row[0] for row in connection.execute(
            "SELECT code FROM market_download_tasks WHERE task_type='daily' AND status='succeeded' ORDER BY code"
        ).fetchall()]
    if not codes:
        return []
    indexes = np.linspace(0, len(codes) - 1, min(sample_size, len(codes)), dtype=int)
    return [str(codes[index]) for index in indexes]


def _stored_bars(path: Path, code: str, config: MarketDataConfig) -> pd.DataFrame:
    query = """SELECT code,trade_date,open,high,low,close,preclose,volume,amount,turnover,
    trade_status,pct_change,is_st,adjustflag FROM daily_bars
    WHERE code=? AND trade_date BETWEEN ? AND ? AND adjustflag=? ORDER BY trade_date"""
    with sqlite3.connect(path) as connection:
        return pd.read_sql_query(query, connection, params=[code, config.start, config.end, config.adjustflag])
