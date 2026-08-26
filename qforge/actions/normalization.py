"""Lossless source envelope plus explicitly nullable parsed dividend fields."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd


NORMALIZATION_VERSION = 2
DATE_FIELDS = {"dividRegistDate": "record_date", "dividOperateDate": "ex_date",
               "dividPayDate": "payment_date", "dividStockMarketDate": "shares_listing_date"}
NUMBER_FIELDS = {"dividCashPsBeforeTax": "gross_cash_per_share",
                 "dividCashPsAfterTax": "source_after_tax_cash_per_share",
                 "dividStocksPs": "source_stock_per_share",
                 "dividReserveToStockPs": "reserve_to_stock_per_share"}
TEXT_FIELDS = {"dividCashStock": "source_cash_stock", "dividCashPsAfterTax": "source_after_tax_text"}
REQUIRED_FIELDS = {"code", *DATE_FIELDS, *NUMBER_FIELDS, *TEXT_FIELDS}


def normalize_response(frame: pd.DataFrame, code: str, year: int) -> tuple[dict, list[dict]]:
    identity = {"code": code, "year": year, "yearType": "operate"}
    if frame.attrs.get("request") != identity:
        raise ValueError("dividend request identity is absent or mismatched")
    if not REQUIRED_FIELDS <= set(frame.columns) or not frame.columns.is_unique:
        raise ValueError("dividend response schema is incomplete or ambiguous")
    raw_rows = frame.to_dict(orient="records")
    events = []
    for raw in raw_rows:
        if raw["code"] != code or any(not isinstance(value, str) for value in raw.values()):
            raise ValueError("dividend raw values must be strings for the requested security")
        issues = []
        event = {target: parse_date(raw[source], source, issues) for source, target in DATE_FIELDS.items()}
        event.update({target: parse_number(raw[source], source, issues) for source, target in NUMBER_FIELDS.items()})
        event.update({target: raw[source] for source, target in TEXT_FIELDS.items()})
        if event["ex_date"] and int(event["ex_date"][:4]) != year:
            raise ValueError("dividend ex-date is outside the requested operate year")
        event.update(code=code, issues=issues, investor_tax_verified=False, ledger_ready=False,
                     normalization_version=NORMALIZATION_VERSION)
        events.append(event)
    dates = [event["ex_date"] for event in events if event["ex_date"]]
    for event in events:
        if event["ex_date"] and dates.count(event["ex_date"]) > 1:
            event["issues"].append("multiple_rows_on_same_ex_date")
    return {"request": identity, "fields": list(frame.columns), "rows": raw_rows}, events


def parse_date(raw: str, field: str, issues: list[str]) -> str | None:
    try:
        parsed = date.fromisoformat(raw)
        if parsed.isoformat() != raw:
            raise ValueError("not canonical ISO date")
        return parsed.isoformat()
    except ValueError:
        issues.append(f"{'missing' if not raw else 'invalid'}:{field}")
        return None


def parse_number(raw: str, field: str, issues: list[str]) -> str | None:
    if field == "dividCashPsAfterTax" and "或" in raw:
        issues.append(f"ambiguous:{field}")
        return None
    try:
        value = Decimal(raw)
        if not value.is_finite() or value < 0:
            raise InvalidOperation
        return str(value)
    except InvalidOperation:
        issues.append(f"{'missing' if not raw else 'invalid'}:{field}")
        return None
