import pandas as pd

from qforge.minute.config import MinuteConfig
from qforge.minute.provider import normalize_frame, normalize_symbol


def config() -> MinuteConfig:
    return MinuteConfig("test", "minute.sqlite", 5, 3, "2026-08-01", "2026-08-24", ["sh.600519"])


def test_symbol_normalization() -> None:
    assert normalize_symbol("600519.SS") == "sh.600519"
    assert normalize_symbol("000001.SZ") == "sz.000001"
    assert normalize_symbol("300750") == "sz.300750"


def test_baostock_minute_fields_are_normalized() -> None:
    raw = pd.DataFrame([{
        "date": "2026-08-24", "time": "20260824093500000", "code": "sh.600519",
        "open": "1500", "high": "1510", "low": "1499", "close": "1508",
        "volume": "1000", "amount": "1505000", "adjustflag": "3",
    }])
    result = normalize_frame(raw, config())
    assert result.loc[0, "bar_time"] == pd.Timestamp("2026-08-24 09:35:00")
    assert result.loc[0, "close"] == 1508.0

