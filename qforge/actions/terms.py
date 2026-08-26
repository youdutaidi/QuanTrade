"""Pure, conservative source-term interpretation; never an investor cash ledger."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation


NUMBER = r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?"
PLAN = re.compile(
    rf"10(?P<legs>(?:送{NUMBER}股?|转(?:增)?{NUMBER}股?|派{NUMBER}元)+)"
    rf"(?P<tax>\(含税(?:,扣税后{NUMBER}(?:或{NUMBER})*元)?\))?"
)
LEG = re.compile(rf"(送|转增|转|派)({NUMBER})(?:股|元)?")
LEG_NAMES = {"送": "bonus_per_share", "转": "reserve_per_share", "转增": "reserve_per_share",
             "派": "gross_cash_per_share"}
NUMERIC_LEGS = {"dividCashPsBeforeTax": "gross_cash_per_share", "dividStocksPs": "bonus_per_share",
                "dividReserveToStockPs": "reserve_per_share"}


def merge_source_rows(rows: list[dict]) -> dict:
    """Fill only complementary blanks; no latest-row preference or summation."""
    if not rows or any(set(row) != set(rows[0]) for row in rows):
        raise ValueError("inconsistent_source_schema")
    if any(not isinstance(value, str) for row in rows for value in row.values()):
        raise ValueError("nonstring_source_value")
    merged = {}
    for field in sorted(rows[0]):
        values = {row[field] for row in rows if row[field] != ""}
        if len(values) > 1:
            raise ValueError(f"conflicting_field:{field}")
        merged[field] = next(iter(values), "")
    if not re.fullmatch(r"(?:sh\.(?:60|68)|sz\.(?:00|30))[0-9]{4}", merged.get("code", "")):
        raise ValueError("invalid_security_identity")
    return merged


def parse_complete_plan(description: str) -> dict:
    """Zeros mean absent legs in this exact grammar, never a numeric NULL fill."""
    text = description.strip().translate(str.maketrans({"（": "(", "）": ")", "，": ","}))
    match = PLAN.fullmatch(text)
    if match is None:
        raise ValueError("unsupported_complete_plan")
    values, seen = dict.fromkeys(NUMERIC_LEGS.values(), Decimal(0)), set()
    for kind, amount in LEG.findall(match["legs"]):
        target = LEG_NAMES[kind]
        if target in seen:
            raise ValueError("duplicate_distribution_leg")
        seen.add(target)
        values[target] = Decimal(amount) / Decimal(10)
    if not any(values.values()):
        raise ValueError("zero_distribution_plan")
    return {**values, "explicit_gross_description": match["tax"] is not None}


def _numeric_agreement(row: dict, terms: dict) -> None:
    for field, term in NUMERIC_LEGS.items():
        raw = row.get(field, "")
        if raw == "":
            continue
        try:
            value = Decimal(raw)
            if not value.is_finite() or value < 0:
                raise InvalidOperation
        except InvalidOperation as error:
            raise ValueError(f"invalid_numeric:{field}") from error
        if value != terms[term]:
            raise ValueError(f"numeric_plan_conflict:{field}")
    if terms["gross_cash_per_share"] and not (terms["explicit_gross_description"] or row.get("dividCashPsBeforeTax")):
        raise ValueError("cash_tax_basis_missing")


def _date(row: dict, field: str, required: bool = True) -> str | None:
    raw = row.get(field, "")
    if raw == "" and not required:
        return None
    try:
        if date.fromisoformat(raw).isoformat() != raw:
            raise ValueError
    except ValueError as error:
        raise ValueError(f"missing_or_invalid_date:{field}") from error
    return raw


def _chronology(row: dict, terms: dict) -> dict:
    announcement = _date(row, "dividPlanDate")
    record, ex_date = _date(row, "dividRegistDate"), _date(row, "dividOperateDate")
    payment = _date(row, "dividPayDate", bool(terms["gross_cash_per_share"]))
    listing = _date(row, "dividStockMarketDate", bool(terms["bonus_per_share"] + terms["reserve_per_share"]))
    if not announcement <= record < ex_date:
        raise ValueError("invalid_announcement_record_ex_chronology")
    if (payment and payment < ex_date) or (listing and listing < ex_date):
        raise ValueError("settlement_before_ex_date")
    return {"implementation_notice_date": announcement, "record_date": record, "ex_date": ex_date,
            "payment_date": payment, "shares_listing_date": listing}


def resolve_source_group(rows: list[dict]) -> dict:
    """A source-consistent gross event is still unfit for economic consumption."""
    result = {"sourceRows": len(rows), "ledgerReady": False, "investorTaxVerified": False}
    try:
        merged = merge_source_rows(rows)
        terms = parse_complete_plan(merged.get("dividCashStock", ""))
        _numeric_agreement(merged, terms)
        dates = _chronology(merged, terms)
        quantities = {name: str(terms[name]) for name in NUMERIC_LEGS.values()}
    except ValueError as error:
        return {**result, "state": "unresolved", "reason": str(error)}
    return {**result, "state": "gross-source-consistent", "terms": {"code": merged["code"], **dates, **quantities},
            "quantityBasis": "complete per-ten-share description; every nonblank numeric leg agrees",
            "taxBasis": "gross cash only; no source after-tax branch selected",
            "identityBasis": "same security/ex-date and no conflicting nonblank source fields"}
