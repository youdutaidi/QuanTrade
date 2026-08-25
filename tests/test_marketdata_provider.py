from __future__ import annotations

from types import SimpleNamespace

from qforge.marketdata.provider import BaoStockMarketProvider


class Response:
    error_code = "0"
    error_msg = "success"
    fields = ["date", "code", "open", "high", "low", "close", "preclose", "volume", "amount", "adjustflag", "turn", "tradestatus", "pctChg", "isST"]

    def __init__(self) -> None:
        self.rows = iter([["2020-01-02", "sh.600000", "10", "11", "9", "10.5", "10", "1000", "10000", "3", "1.2", "1", "5", "0"]])
        self.current = None

    def next(self) -> bool:
        self.current = next(self.rows, None)
        return self.current is not None

    def get_row_data(self):
        return self.current


def test_daily_provider_normalizes_numeric_fields() -> None:
    module = SimpleNamespace(query_history_k_data_plus=lambda *args, **kwargs: Response())
    provider = BaoStockMarketProvider(module=module)
    frame = provider.daily_bars("sh.600000", "2020-01-01", "2020-01-03", 3)
    assert frame.iloc[0]["code"] == "sh.600000"
    assert frame.iloc[0]["close"] == 10.5
    assert frame.iloc[0]["trade_status"] == 1
