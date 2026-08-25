"""BaoStock adapter with normalized frames and bounded socket waits."""

from __future__ import annotations

import signal
from contextlib import contextmanager
from types import ModuleType

import pandas as pd


DAILY_FIELDS = "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST"
DAILY_NUMERIC = ["open", "high", "low", "close", "preclose", "volume", "amount", "turn", "tradestatus", "pctChg", "isST"]


class BaoStockMarketProvider:
    def __init__(self, module: ModuleType | None = None, timeout_seconds: int = 90):
        self.module = module
        self.timeout_seconds = timeout_seconds

    def __enter__(self) -> "BaoStockMarketProvider":
        if self.module is None:
            import baostock as bs

            self.module = bs
        with _deadline(self.timeout_seconds):
            response = self.module.login()
        if response.error_code != "0":
            raise RuntimeError(f"BaoStock login failed: {response.error_msg}")
        return self

    def __exit__(self, *_: object) -> None:
        if self.module is not None:
            with _deadline(self.timeout_seconds):
                self.module.logout()

    def trade_calendar(self, start: str, end: str) -> pd.DataFrame:
        with _deadline(self.timeout_seconds):
            response = self.module.query_trade_dates(start_date=start, end_date=end)
        return self._query(response)

    def security_master(self) -> pd.DataFrame:
        with _deadline(self.timeout_seconds):
            response = self.module.query_stock_basic()
        return self._query(response)

    def universe(self, day: str) -> pd.DataFrame:
        with _deadline(self.timeout_seconds):
            response = self.module.query_all_stock(day=day)
        return self._query(response)

    def daily_bars(self, code: str, start: str, end: str, adjustflag: int) -> pd.DataFrame:
        with _deadline(self.timeout_seconds):
            response = self.module.query_history_k_data_plus(
                code,
                DAILY_FIELDS,
                start_date=start,
                end_date=end,
                frequency="d",
                adjustflag=str(adjustflag),
            )
        frame = self._query(response)
        if frame.empty:
            return _empty_daily()
        result = frame.rename(
            columns={"date": "trade_date", "turn": "turnover", "tradestatus": "trade_status", "pctChg": "pct_change", "isST": "is_st"}
        ).copy()
        for field in DAILY_NUMERIC:
            target = {"turn": "turnover", "tradestatus": "trade_status", "pctChg": "pct_change", "isST": "is_st"}.get(field, field)
            result[target] = pd.to_numeric(result[target], errors="coerce")
        result["adjustflag"] = pd.to_numeric(result["adjustflag"], errors="coerce").fillna(adjustflag).astype(int)
        result["source"] = "BaoStock"
        return result[_daily_columns()]

    def adjustment_factors(self, code: str, start: str, end: str) -> pd.DataFrame:
        with _deadline(self.timeout_seconds):
            response = self.module.query_adjust_factor(code=code, start_date=start, end_date=end)
        frame = self._query(response)
        if frame.empty:
            return pd.DataFrame(columns=["code", "operation_date", "fore_adjust_factor", "back_adjust_factor", "adjust_factor", "source"])
        result = frame.rename(
            columns={
                "dividOperateDate": "operation_date",
                "foreAdjustFactor": "fore_adjust_factor",
                "backAdjustFactor": "back_adjust_factor",
                "adjustFactor": "adjust_factor",
            }
        ).copy()
        for field in ["fore_adjust_factor", "back_adjust_factor", "adjust_factor"]:
            result[field] = pd.to_numeric(result[field], errors="coerce")
        result["source"] = "BaoStock"
        columns = ["code", "operation_date", "fore_adjust_factor", "back_adjust_factor", "adjust_factor", "source"]
        return result[columns].dropna(subset=["operation_date"])

    def _query(self, response: object) -> pd.DataFrame:
        if response.error_code != "0":
            raise RuntimeError(f"BaoStock query error {response.error_code}: {response.error_msg}")
        rows: list[list[str]] = []
        with _deadline(self.timeout_seconds):
            while response.error_code == "0" and response.next():
                rows.append(response.get_row_data())
        return pd.DataFrame(rows, columns=response.fields)


class ProviderTimeout(TimeoutError):
    """Raised when BaoStock stops responding inside one bounded request."""


@contextmanager
def _deadline(seconds: int):
    if not hasattr(signal, "SIGALRM"):
        yield
        return
    previous = signal.getsignal(signal.SIGALRM)

    def timeout_handler(_signum: int, _frame: object) -> None:
        raise ProviderTimeout(f"BaoStock request exceeded {seconds} seconds")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _daily_columns() -> list[str]:
    return [
        "code", "trade_date", "open", "high", "low", "close", "preclose", "volume", "amount",
        "adjustflag", "turnover", "trade_status", "pct_change", "is_st", "source",
    ]


def _empty_daily() -> pd.DataFrame:
    return pd.DataFrame(columns=_daily_columns())
