"""Create adjusted-price features, not an economic total-return ledger."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pandas as pd

from .export import write_panel_chunks


RAW_DAILY_QUERY = """SELECT b.code,b.trade_date,b.open,b.high,b.low,b.close,b.preclose,b.volume,b.amount,
b.turnover,b.trade_status,b.pct_change,b.is_st
FROM daily_bars b JOIN listed_universe u ON u.trade_date=b.trade_date AND u.code=b.code
WHERE b.trade_date BETWEEN ? AND ? AND b.adjustflag=?"""


def load_raw_daily(path: str | Path, start: str, end: str, adjustflag: int = 3) -> pd.DataFrame:
    with sqlite3.connect(path) as connection:
        return pd.read_sql_query(RAW_DAILY_QUERY + " ORDER BY b.code,b.trade_date", connection, params=[start, end, adjustflag])


def iter_raw_daily_chunks(
    path: str | Path, start: str, end: str, adjustflag: int = 3, symbols_per_chunk: int = 100,
) -> Iterator[pd.DataFrame]:
    if symbols_per_chunk < 1:
        raise ValueError("symbols per chunk must be positive")
    with sqlite3.connect(path) as connection:
        connection.execute("BEGIN")  # Every chunk observes one consistent SQLite snapshot.
        codes = [row[0] for row in connection.execute(
            "SELECT DISTINCT code FROM daily_bars WHERE trade_date BETWEEN ? AND ? AND adjustflag=? ORDER BY code",
            (start, end, adjustflag),
        )]
        for offset in range(0, len(codes), symbols_per_chunk):
            batch = codes[offset:offset + symbols_per_chunk]
            query = RAW_DAILY_QUERY + f" AND b.code IN ({','.join('?' for _ in batch)}) ORDER BY b.code,b.trade_date"
            frame = pd.read_sql_query(query, connection, params=[start, end, adjustflag, *batch])
            if not frame.empty:
                yield frame


def adjusted_price_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    """Chain exchange reference-price returns for signals; preserve raw prices.

    Dividends, rights, share changes, taxes and execution still require a separate
    cash/share ledger. This price chain must not certify corporate-action P&L.
    """
    if frame.empty:
        return pd.DataFrame(columns=_output_columns())
    required = {"code", "trade_date", "open", "high", "low", "close", "preclose", "volume", "amount", "trade_status", "pct_change", "is_st"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"raw daily frame missing columns: {sorted(missing)}")
    if frame.duplicated(["code", "trade_date"]).any():
        raise ValueError("raw daily frame contains duplicate keys")
    result = frame.copy().sort_values(["code", "trade_date"])
    result["date"] = pd.to_datetime(result["trade_date"])
    result["symbol"] = result["code"].astype(str)
    for field in ["open", "high", "low", "close", "preclose"]:
        result[f"raw_{field}"] = pd.to_numeric(result[field], errors="coerce")
    growth = _reference_growth(result)
    adjusted_close = growth.groupby(result["symbol"]).cumprod()
    previous_index = adjusted_close.div(growth)
    for field in ["open", "high", "low"]:
        ratio = result[field].div(result["preclose"].replace(0, np.nan))
        result[field] = previous_index.mul(ratio)
    result["close"] = adjusted_close
    suspended = pd.to_numeric(result["trade_status"], errors="coerce").ne(1)
    result.loc[suspended, ["open", "high", "low"]] = np.nan
    prices = result.loc[~suspended, ["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError("invalid adjusted prices on a tradable day")
    result["volume"] = pd.to_numeric(result["volume"], errors="coerce").fillna(0)
    return result[_output_columns()]


def total_return_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    """Legacy alias; the result is an adjusted-price chain, NOT total return."""
    return adjusted_price_ohlcv(frame)


def _reference_growth(frame: pd.DataFrame) -> pd.Series:
    status = pd.to_numeric(frame["trade_status"], errors="coerce")
    if not status.isin([0, 1]).all():
        raise ValueError("invalid trade status in raw daily frame")
    fallback = frame["raw_close"].div(frame["raw_preclose"].replace(0, np.nan)).sub(1)
    returns = pd.to_numeric(frame["pct_change"], errors="coerce").div(100).fillna(fallback)
    returns = returns.mask(status.eq(0), 0.0)
    if not np.isfinite(returns).all() or returns.le(-1).any():
        raise ValueError("invalid reference-price return; extreme losses must not be clipped or filled")
    return returns.add(1)


def export_research_panel(
    database_path: str | Path,
    output_path: str | Path,
    start: str,
    end: str,
    adjustflag: int = 3,
    symbols_per_chunk: int = 100,
) -> dict[str, object]:
    if adjustflag != 3:
        raise ValueError("research panel requires raw unadjusted bars (adjustflag=3)")
    raw_chunks = iter_raw_daily_chunks(database_path, start, end, adjustflag, symbols_per_chunk)
    metadata = {
        "price_basis": "exchange_reference_price_chain", "corporate_actions_verified": "false",
        "start": start, "end": end, "adjustflag": str(adjustflag),
    }
    stats = write_panel_chunks((adjusted_price_ohlcv(raw) for raw in raw_chunks), output_path, metadata)
    return {
        **stats,
        "symbolsPerChunk": symbols_per_chunk,
        "priceBasis": "exchange-reference-price chain; raw OHLC also retained",
        "corporateActionsVerified": False,
        "permittedUse": "signal research; not a cash/share P&L ledger",
    }


def _output_columns() -> list[str]:
    return [
        "date", "symbol", "open", "high", "low", "close", "volume", "amount", "turnover", "trade_status", "is_st",
        "raw_open", "raw_high", "raw_low", "raw_close", "raw_preclose",
    ]
