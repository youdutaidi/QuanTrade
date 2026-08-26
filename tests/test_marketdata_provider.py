from __future__ import annotations

from types import SimpleNamespace

import pytest

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


def test_provider_rejects_error_after_partial_stream() -> None:
    class BrokenResponse(Response):
        def next(self):
            if self.current is not None:
                self.error_code, self.error_msg = "10002007", "stream failed"
                return False
            return super().next()

    provider = BaoStockMarketProvider(module=SimpleNamespace(
        query_history_k_data_plus=lambda *args, **kwargs: BrokenResponse(),
    ))
    with pytest.raises(RuntimeError, match="partial stream"):
        provider.daily_bars("sh.600000", "2020-01-01", "2020-01-03", 3)


def test_provider_rejects_unconfirmed_full_page_eof() -> None:
    response = Response()
    response.data = [None] * 2000
    response.cur_row_num = 2000
    provider = BaoStockMarketProvider(module=SimpleNamespace(
        query_history_k_data_plus=lambda *args, **kwargs: response,
    ))
    with pytest.raises(RuntimeError, match="confirmed EOF"):
        provider.daily_bars("sh.600000", "2020-01-01", "2020-01-03", 3)


@pytest.mark.parametrize("code,start,end,flag", [
    ("sh.600001", "2020-01-01", "2020-01-03", 3),
    ("sh.600000", "2020-01-03", "2020-01-04", 3),
    ("sh.600000", "2020-01-01", "2020-01-03", 2),
])
def test_provider_rejects_wrong_response_identity(code, start, end, flag) -> None:
    provider = BaoStockMarketProvider(module=SimpleNamespace(
        query_history_k_data_plus=lambda *args, **kwargs: Response(),
    ))
    with pytest.raises(ValueError):
        provider.daily_bars(code, start, end, flag)


def test_adjustment_provider_rejects_wrong_security_code():
    response = Response()
    response.fields = ["code", "dividOperateDate", "foreAdjustFactor", "backAdjustFactor", "adjustFactor"]
    response.rows = iter([["sh.600001", "2020-06-01", "0.9", "1.2", "1.02"]])
    provider = BaoStockMarketProvider(module=SimpleNamespace(query_adjust_factor=lambda **kwargs: response))
    with pytest.raises(ValueError, match="unexpected security"):
        provider.adjustment_factors("sh.600000", "2020-01-01", "2020-12-31")
