import pandas as pd
import pytest

from qforge.actions.normalization import REQUIRED_FIELDS, normalize_response


def raw_frame(**changes):
    row = {key: "" for key in REQUIRED_FIELDS}
    row.update(code="sh.600000", dividOperateDate="2021-07-01", dividCashPsBeforeTax="0.16000000")
    row.update(changes)
    frame = pd.DataFrame([row])
    frame.attrs["request"] = {"code": "sh.600000", "year": 2021, "yearType": "operate"}
    return frame


def test_raw_precision_and_missing_values_are_preserved():
    raw, events = normalize_response(raw_frame(), "sh.600000", 2021)
    assert raw["rows"][0]["dividCashPsBeforeTax"] == "0.16000000"
    event = events[0]
    assert event["gross_cash_per_share"] == "0.16000000"
    assert event["source_after_tax_cash_per_share"] is None
    assert event["source_stock_per_share"] is None
    assert "missing:dividPayDate" in event["issues"]
    assert event["ledger_ready"] is event["investor_tax_verified"] is False


def test_bad_numeric_dates_and_duplicates_remain_auditable():
    frame = raw_frame(dividCashPsAfterTax="NaN", dividRegistDate="20210230")
    frame = pd.concat([frame, frame], ignore_index=True)
    raw, events = normalize_response(frame, "sh.600000", 2021)
    assert len(raw["rows"]) == len(events) == 2
    assert raw["rows"][0]["dividRegistDate"] == "20210230"
    assert events[0]["record_date"] is None
    assert {"multiple_rows_on_same_ex_date", "invalid:dividCashPsAfterTax", "invalid:dividRegistDate"} <= set(events[0]["issues"])


@pytest.mark.parametrize("changes", [{"code": "sh.600001"}, {"dividOperateDate": "2022-07-01"}, {"dividStocksPs": 0}])
def test_wrong_row_identity_or_lossy_type_rejected(changes):
    with pytest.raises(ValueError):
        normalize_response(raw_frame(**changes), "sh.600000", 2021)


def test_empty_year_is_valid_only_with_schema_and_identity():
    frame = raw_frame().iloc[:0].copy()
    raw, events = normalize_response(frame, "sh.600000", 2021)
    assert events == raw["rows"] == []
    assert set(raw["fields"]) == REQUIRED_FIELDS
    frame.attrs.clear()
    with pytest.raises(ValueError, match="request identity"):
        normalize_response(frame, "sh.600000", 2021)


def test_missing_column_is_not_silently_defaulted_to_zero():
    with pytest.raises(ValueError, match="schema"):
        normalize_response(raw_frame().drop(columns="dividCashPsAfterTax"), "sh.600000", 2021)


def test_real_source_description_and_ambiguous_tax_are_not_numeric_claims():
    description = "10派6元（含税，扣税后5.4或6元）"
    raw, events = normalize_response(raw_frame(dividCashStock=description,
                                             dividCashPsAfterTax="0.54或0.6"), "sh.600000", 2021)
    event = events[0]
    assert event["source_cash_stock"] == raw["rows"][0]["dividCashStock"] == description
    assert event["source_after_tax_text"] == "0.54或0.6"
    assert event["source_after_tax_cash_per_share"] is None
    assert "ambiguous:dividCashPsAfterTax" in event["issues"]
    assert "invalid:dividCashStock" not in event["issues"]
    assert event["normalization_version"] == 2
    assert event["ledger_ready"] is event["investor_tax_verified"] is False


def test_single_after_tax_value_retains_precision_but_is_not_investor_tax_proof():
    _, events = normalize_response(raw_frame(dividCashPsAfterTax="0.540000"), "sh.600000", 2021)
    assert events[0]["source_after_tax_cash_per_share"] == "0.540000"
    assert events[0]["source_after_tax_text"] == "0.540000"
    assert events[0]["source_cash_stock"] == ""
    assert events[0]["investor_tax_verified"] is False
