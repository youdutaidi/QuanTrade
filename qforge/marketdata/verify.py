"""Fresh-source sample replay for detecting silent ingestion corruption."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from .config import MarketDataConfig
from .provider import BaoStockMarketProvider


NUMERIC_FIELDS = ["open", "high", "low", "close", "preclose", "volume", "amount", "turnover", "trade_status", "pct_change", "is_st"]
ADJUSTMENT_FIELDS = ["fore_adjust_factor", "back_adjust_factor", "adjust_factor"]


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
            fresh_factors = provider.adjustment_factors(code, config.start, config.end)
            stored_factors = _stored_adjustments(path, code, config)
            factors = compare_adjustment_frames(fresh_factors, stored_factors)
            status = "pass" if result["status"] == factors["status"] == "pass" else "mismatch"
            results.append({"code": code, "status": status, "daily": result, "adjustments": factors})
    return {
        "sampleSize": len(codes),
        "allPass": bool(results) and all(item["status"] == "pass" for item in results),
        "results": results,
        "scope": "same-source replay of daily bars and adjustment factors; not independent market or P&L verification",
        "samplePolicy": "deterministic evenly-spaced securities with explicit lifecycle and board coverage",
    }


def compare_daily_frames(fresh: pd.DataFrame, stored: pd.DataFrame) -> dict[str, object]:
    return _compare_frames(fresh, stored, ["code", "trade_date", "adjustflag"], NUMERIC_FIELDS)


def compare_adjustment_frames(fresh: pd.DataFrame, stored: pd.DataFrame) -> dict[str, object]:
    return _compare_frames(fresh, stored, ["code", "operation_date"], ADJUSTMENT_FIELDS)


def _compare_frames(fresh: pd.DataFrame, stored: pd.DataFrame, keys: list[str], numeric: list[str]) -> dict[str, object]:
    fields = [*keys, *numeric]
    if set(fields) - set(fresh.columns) or set(fields) - set(stored.columns):
        return {"status": "mismatch", "reason": "missing_columns"}
    if fresh.duplicated(keys).any() or stored.duplicated(keys).any():
        return {"status": "mismatch", "reason": "duplicate_keys"}
    left = fresh[fields].sort_values(keys).reset_index(drop=True)
    right = stored[fields].sort_values(keys).reset_index(drop=True)
    if len(left) != len(right):
        return {"status": "mismatch", "freshRows": len(left), "storedRows": len(right), "reason": "row_count"}
    if len(left) and not left[keys].equals(right[keys]):
        return {"status": "mismatch", "freshRows": len(left), "storedRows": len(right), "reason": "keys"}
    mismatches = 0
    for field in numeric:
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
    if sample_size < 1:
        raise ValueError("sample size must be positive")
    with sqlite3.connect(path) as connection:
        rows = connection.execute("""SELECT DISTINCT t.code,s.out_date,s.security_type,
            EXISTS(SELECT 1 FROM adjustment_factors f WHERE f.code=t.code) has_adjustments
            FROM market_download_tasks t JOIN securities s ON s.code=t.code
            WHERE t.task_type='daily' AND t.status='succeeded' ORDER BY t.code""").fetchall()
    codes = [row[0] for row in rows]
    if not codes:
        return []
    targets = min(sample_size, len(codes))
    required = [next((r[0] for r in rows if predicate(r)), None) for predicate in [
        lambda r: r[1] is not None, lambda r: r[2] == "2", lambda r: r[3],
        lambda r: r[0].startswith("sh.60"), lambda r: r[0].startswith("sh.68"),
        lambda r: r[0].startswith("sz.00"), lambda r: r[0].startswith("sz.30"),
    ]]
    spaced = [codes[i] for i in np.linspace(0, len(codes) - 1, targets, dtype=int)]
    return list(dict.fromkeys(code for code in [*required, *spaced, *codes] if code))[:targets]


def _stored_bars(path: Path, code: str, config: MarketDataConfig) -> pd.DataFrame:
    query = """SELECT code,trade_date,open,high,low,close,preclose,volume,amount,turnover,
    trade_status,pct_change,is_st,adjustflag FROM daily_bars
    WHERE code=? AND trade_date BETWEEN ? AND ? AND adjustflag=? ORDER BY trade_date"""
    with sqlite3.connect(path) as connection:
        return pd.read_sql_query(query, connection, params=[code, config.start, config.end, config.adjustflag])


def _stored_adjustments(path: Path, code: str, config: MarketDataConfig) -> pd.DataFrame:
    query = """SELECT code,operation_date,fore_adjust_factor,back_adjust_factor,adjust_factor
    FROM adjustment_factors WHERE code=? AND operation_date BETWEEN ? AND ? ORDER BY operation_date"""
    with sqlite3.connect(path) as connection:
        return pd.read_sql_query(query, connection, params=[code, config.start, config.end])
