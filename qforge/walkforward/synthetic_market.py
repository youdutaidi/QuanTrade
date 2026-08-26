"""Deterministic test-only market fixture; never labels generated bars as sourced."""

from __future__ import annotations

import math

import pandas as pd

from .models import Distribution
from .specification import StudySpec


def synthetic_market(spec: StudySpec) -> tuple[pd.DataFrame, list[str], pd.DataFrame, tuple[Distribution, ...]]:
    calendar = pd.bdate_range(spec.values["periods"]["discovery"][0], periods=420).strftime("%Y-%m-%d").tolist()
    codes = ["sh.600000", "sz.000001", "sz.300001", spec.values["benchmark"]]
    records, references = [], {}
    for index, code in enumerate(codes):
        price, feature = (10.0 * (index + 1) if index < 3 else 1000.0), 1.0
        for position, day in enumerate(calendar):
            reference = round((price - 0.2) / 1.1, 2) if index == 0 and position == 405 else price
            change = 0.0015 * math.sin(position / (7 + index) + index) + 0.0003 * math.cos(position / 3 + index)
            opening = round(reference * (1 + 0.0004 * math.sin(position + index)), 2)
            close = round(reference * (1 + change), 2)
            feature *= close / reference
            records.append({"date": pd.Timestamp(day), "symbol": code, "close": feature,
                            "raw_open": opening, "raw_close": close, "raw_preclose": reference,
                            "volume": 40000000.0, "amount": close * 40000000.0,
                            "trade_status": 1, "is_st": 0})
            references[(code, day)], price = reference, close
    securities = pd.DataFrame([{"code": code, "ipo_date": "2010-01-01", "out_date": None,
                                "security_type": "1" if index < 3 else "2", "current_status": "1"}
                               for index, code in enumerate(codes)])
    action = Distribution("synthetic-distribution", codes[0], calendar[404], calendar[405],
                          0.16, 0.1, calendar[407], calendar[407], references[(codes[0], calendar[405])],
                          "synthetic-only", "explicit synthetic 20-percent cash haircut, not investor tax evidence")
    return pd.DataFrame(records), calendar, securities, (action,)
