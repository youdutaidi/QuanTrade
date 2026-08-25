"""Fetch a reproducible current-constituent CSI 800 research snapshot and Yahoo OHLCV."""

from __future__ import annotations

import json
import time
from pathlib import Path

import akshare as ak
import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research/data"
START = "2024-07-01"
END_EXCLUSIVE = "2026-08-26"
INDEX_CODES = ("000300", "000905")
BENCHMARKS = {"000001.SS": "上证综指", "000300.SS": "沪深300"}


def yahoo_symbol(code: str, exchange: str) -> str:
    if "上海" in exchange:
        return f"{code}.SS"
    return f"{code}.SZ"


def fetch_chunk(symbols: list[str]) -> pd.DataFrame:
    return yf.download(
        symbols,
        start=START,
        end=END_EXCLUSIVE,
        auto_adjust=True,
        repair=False,
        actions=False,
        progress=False,
        group_by="column",
        threads=True,
        timeout=30,
    )


def to_long(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    if not isinstance(frame.columns, pd.MultiIndex):
        raise ValueError("Expected multi-index Yahoo columns")
    long = frame.stack(level="Ticker", future_stack=True).reset_index()
    long.columns.name = None
    long = long.rename(columns={"Date": "date", "Ticker": "symbol"})
    long.columns = [str(col).lower().replace(" ", "_") for col in long.columns]
    return long


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    yf.set_tz_cache_location(str(DATA / "yf_cache"))

    members = []
    for index_code in INDEX_CODES:
        frame = ak.index_stock_cons_csindex(symbol=index_code).copy()
        frame["universe"] = "CSI300" if index_code == "000300" else "CSI500"
        members.append(frame)
    membership = pd.concat(members, ignore_index=True)
    membership["symbol"] = membership.apply(
        lambda row: yahoo_symbol(str(row["成分券代码"]).zfill(6), str(row["交易所"])), axis=1
    )
    membership = membership.rename(
        columns={"日期": "snapshot_date", "成分券代码": "code", "成分券名称": "name", "交易所": "exchange"}
    )[["snapshot_date", "universe", "code", "name", "exchange", "symbol"]]
    membership.to_csv(DATA / "csi800_membership_snapshot.csv", index=False)

    symbols = membership["symbol"].drop_duplicates().tolist() + list(BENCHMARKS)
    chunks: list[pd.DataFrame] = []
    failures: list[str] = []
    for offset in range(0, len(symbols), 60):
        batch = symbols[offset : offset + 60]
        for attempt in range(3):
            try:
                downloaded = fetch_chunk(batch)
                long = to_long(downloaded)
                if not long.empty:
                    chunks.append(long)
                    available = set(long.loc[long["close"].notna(), "symbol"].unique())
                    failures.extend(sorted(set(batch) - available))
                break
            except Exception as exc:  # network retries are recorded below
                if attempt == 2:
                    print(f"batch_failed offset={offset} error={exc!r}")
                    failures.extend(batch)
                else:
                    time.sleep(2 ** attempt)
        print(f"downloaded {min(offset + len(batch), len(symbols))}/{len(symbols)}")

    market = pd.concat(chunks, ignore_index=True)
    market = market.drop_duplicates(["date", "symbol"]).sort_values(["symbol", "date"])
    market.to_parquet(DATA / "csi800_ohlcv.parquet", index=False)

    summary = {
        "source": "Yahoo Finance adjusted OHLCV",
        "membership_source": "China Securities Index official current constituent files via AkShare",
        "membership_snapshot": str(membership["snapshot_date"].max()),
        "requested_symbols": len(symbols),
        "available_symbols": int(market.loc[market["close"].notna(), "symbol"].nunique()),
        "first_date": str(market["date"].min().date()),
        "last_date": str(market["date"].max().date()),
        "failed_symbols": sorted(set(failures)),
        "known_limit": "Current constituents create survivorship bias for a historical backtest.",
    }
    (DATA / "market_data_manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
