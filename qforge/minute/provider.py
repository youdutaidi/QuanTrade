"""BaoStock minute-bar adapter with normalized timestamps and recoverable retries."""

from __future__ import annotations

import time
from types import ModuleType

import pandas as pd

from .config import MinuteConfig
from ..marketdata.session import baostock_session_lock


MINUTE_FIELDS = "date,time,code,open,high,low,close,volume,amount,adjustflag"
NUMERIC_FIELDS = ["open", "high", "low", "close", "volume", "amount"]


def normalize_symbol(symbol: str) -> str:
    raw = symbol.strip()
    if raw.startswith(("sh.", "sz.")):
        return raw.lower()
    upper = raw.upper()
    if upper.endswith(".SS"):
        return f"sh.{upper[:6]}"
    if upper.endswith(".SZ"):
        return f"sz.{upper[:6]}"
    if len(raw) == 6 and raw.isdigit():
        return f"sh.{raw}" if raw.startswith(("5", "6", "9")) else f"sz.{raw}"
    raise ValueError(f"cannot normalize symbol: {symbol}")


class BaoStockProvider:
    def __init__(self, module: ModuleType | None = None, retries: int = 3):
        self.module = module
        self.retries = retries
        self.session_lock = baostock_session_lock()

    def __enter__(self) -> "BaoStockProvider":
        self.session_lock.__enter__()
        try:
            return self._login()
        except BaseException:
            self.session_lock.__exit__()
            raise

    def _login(self) -> "BaoStockProvider":
        if self.module is None:
            import baostock as bs

            self.module = bs
        response = self.module.login()
        if response.error_code != "0":
            raise RuntimeError(f"BaoStock login failed: {response.error_msg}")
        return self

    def __exit__(self, *_: object) -> None:
        try:
            if self.module is not None:
                self.module.logout()
        finally:
            self.session_lock.__exit__()

    def fetch(self, symbol: str, config: MinuteConfig) -> pd.DataFrame:
        code = normalize_symbol(symbol)
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                return self._fetch_once(code, config)
            except Exception as error:
                last_error = error
                if attempt + 1 < self.retries:
                    time.sleep(2**attempt)
        raise RuntimeError(f"BaoStock fetch failed for {code}") from last_error

    def _fetch_once(self, code: str, config: MinuteConfig) -> pd.DataFrame:
        response = self.module.query_history_k_data_plus(
            code,
            MINUTE_FIELDS,
            start_date=config.start,
            end_date=config.end,
            frequency=str(config.frequency),
            adjustflag=str(config.adjustflag),
        )
        if response.error_code != "0":
            raise RuntimeError(f"BaoStock query error {response.error_code}: {response.error_msg}")
        rows = []
        while response.error_code == "0" and response.next():
            rows.append(response.get_row_data())
        return normalize_frame(pd.DataFrame(rows, columns=response.fields), config)


def normalize_frame(frame: pd.DataFrame, config: MinuteConfig) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["symbol", "frequency", "bar_time", "trade_date", *NUMERIC_FIELDS, "adjustflag", "source"])
    result = frame.rename(columns={"code": "symbol"}).copy()
    timestamp = result["time"].astype(str).str.slice(0, 14)
    result["bar_time"] = pd.to_datetime(timestamp, format="%Y%m%d%H%M%S")
    result["trade_date"] = pd.to_datetime(result["date"]).dt.strftime("%Y-%m-%d")
    for field in NUMERIC_FIELDS:
        result[field] = pd.to_numeric(result[field], errors="coerce")
    result["frequency"] = config.frequency
    result["adjustflag"] = pd.to_numeric(result["adjustflag"], errors="coerce").fillna(config.adjustflag).astype(int)
    result["source"] = "BaoStock"
    columns = ["symbol", "frequency", "bar_time", "trade_date", *NUMERIC_FIELDS, "adjustflag", "source"]
    return result[columns].dropna(subset=["bar_time", "open", "high", "low", "close"])
