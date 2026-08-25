"""Market-data adapters with an explicit long-table input contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {"date", "symbol", "open", "high", "low", "close", "volume"}


@dataclass(frozen=True)
class MarketPanel:
    open: pd.DataFrame
    high: pd.DataFrame
    low: pd.DataFrame
    close: pd.DataFrame
    volume: pd.DataFrame
    benchmark: pd.Series | None

    @property
    def dates(self) -> pd.DatetimeIndex:
        return self.close.index

    @property
    def symbols(self) -> pd.Index:
        return self.close.columns


def read_long_market(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if source.suffix.lower() == ".parquet":
        frame = pd.read_parquet(source)
    elif source.suffix.lower() in {".csv", ".gz"}:
        frame = pd.read_csv(source)
    else:
        raise ValueError(f"unsupported market-data format: {source.suffix}")
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"market data missing columns: {sorted(missing)}")
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], utc=True).dt.tz_localize(None)
    frame["symbol"] = frame["symbol"].astype(str)
    return frame.sort_values(["date", "symbol"]).drop_duplicates(["date", "symbol"])


def _wide(frame: pd.DataFrame, field: str) -> pd.DataFrame:
    return frame.pivot(index="date", columns="symbol", values=field).sort_index()


def load_panel(
    data_path: str | Path,
    membership_path: str | Path | None = None,
    benchmark_symbol: str | None = None,
) -> MarketPanel:
    frame = read_long_market(data_path)
    benchmark = _benchmark(frame, benchmark_symbol)
    if membership_path:
        members = pd.read_csv(membership_path, dtype={"symbol": str})
        universe = set(members["symbol"].dropna())
        frame = frame.loc[frame["symbol"].isin(universe)]
    return MarketPanel(
        open=_wide(frame, "open"),
        high=_wide(frame, "high"),
        low=_wide(frame, "low"),
        close=_wide(frame, "close"),
        volume=_wide(frame, "volume"),
        benchmark=benchmark,
    )


def _benchmark(frame: pd.DataFrame, symbol: str | None) -> pd.Series | None:
    if not symbol:
        return None
    selected = frame.loc[frame["symbol"] == symbol, ["date", "close"]]
    if selected.empty:
        raise ValueError(f"benchmark symbol not found: {symbol}")
    return selected.set_index("date")["close"].sort_index().rename(symbol)


def validate_panel(panel: MarketPanel) -> dict[str, object]:
    if panel.close.empty or panel.open.empty:
        raise ValueError("market panel is empty")
    overlap = panel.open.index.intersection(panel.close.index)
    if len(overlap) < 3:
        raise ValueError("market panel needs at least three common dates")
    return {
        "firstDate": str(overlap.min().date()),
        "lastDate": str(overlap.max().date()),
        "dates": len(overlap),
        "symbols": len(panel.symbols),
        "duplicateKeys": 0,
    }

