from decimal import Decimal
from itertools import permutations

import pytest

from qforge.actions.normalization import REQUIRED_FIELDS
from qforge.actions.terms import parse_complete_plan, resolve_source_group


def cash_row(**changes):
    row = {field: "" for field in REQUIRED_FIELDS}
    row.update(code="sh.600000", dividPlanDate="2021-06-20", dividRegistDate="2021-06-30",
               dividOperateDate="2021-07-01", dividPayDate="2021-07-01", dividCashPsBeforeTax="0.6",
               dividCashPsAfterTax="0.54或0.6", dividCashStock="10派6元（含税，扣税后5.4或6元）")
    return {**row, **changes}


def test_duplicates_do_not_double_gross_cash_or_choose_tax_branch():
    row = cash_row()
    before = row.copy()
    result = resolve_source_group([row, row.copy()])
    assert row == before
    assert result["state"] == "gross-source-consistent" and result["sourceRows"] == 2
    assert result["terms"]["gross_cash_per_share"] == "0.6"
    assert result["terms"]["bonus_per_share"] == result["terms"]["reserve_per_share"] == "0"
    assert not result["ledgerReady"] and not result["investorTaxVerified"]
    assert "net_cash_per_share" not in result["terms"]


def test_complementary_missing_fields_merge_without_source_mutation():
    first, second = cash_row(dividCashPsBeforeTax=""), cash_row(dividCashPsAfterTax="")
    result = resolve_source_group([first, second])
    assert result["state"] == "gross-source-consistent"
    assert first["dividCashPsBeforeTax"] == second["dividCashPsAfterTax"] == ""
    assert resolve_source_group([second, first]) == result


@pytest.mark.parametrize("field,value", [("dividCashPsBeforeTax", "0.7"), ("dividCashStock", "10派6元"),
                                         ("dividPayDate", "2021-07-02"), ("dividCashPsAfterTax", "0.6")])
def test_conflicting_duplicates_fail_closed(field, value):
    result = resolve_source_group([cash_row(), cash_row(**{field: value})])
    assert result["state"] == "unresolved" and result["reason"] == f"conflicting_field:{field}"


def test_bonus_and_reserve_are_separate_gross_legs_with_explicit_listing():
    row = cash_row(dividCashStock="10送2转增3派6元（含税）", dividStocksPs="0.200000",
                   dividReserveToStockPs="0.300000", dividStockMarketDate="2021-07-05")
    terms = resolve_source_group([row])["terms"]
    assert terms["bonus_per_share"] == "0.2" and terms["reserve_per_share"] == "0.3"
    assert terms["shares_listing_date"] == "2021-07-05"


def test_explicit_share_only_plan_has_zero_cash_but_blanks_alone_do_not():
    row = cash_row(dividCashStock="10转4", dividCashPsBeforeTax="", dividCashPsAfterTax="",
                   dividPayDate="", dividStockMarketDate="2021-07-01")
    result = resolve_source_group([row])
    assert result["terms"]["gross_cash_per_share"] == "0"
    assert result["terms"]["reserve_per_share"] == "0.4"
    assert result["terms"]["payment_date"] is None
    assert resolve_source_group([{**row, "dividCashStock": ""}])["state"] == "unresolved"


@pytest.mark.parametrize("description", ["", "10派6元（不含税）", "10派6元（税后）", "10转4配2股",
                                         "10派6元另有补偿", "10派-1元", "10", "10派0元", "10派NaN元"])
def test_unknown_or_partial_plan_is_not_treated_as_complete(description):
    assert resolve_source_group([cash_row(dividCashStock=description)])["state"] == "unresolved"


def test_cash_gross_basis_requires_explicit_description_or_matching_gross_field():
    assert resolve_source_group([cash_row(dividCashStock="10派6元")])["state"] == "gross-source-consistent"
    result = resolve_source_group([cash_row(dividCashStock="10派6元", dividCashPsBeforeTax="")])
    assert result["reason"] == "cash_tax_basis_missing"
    assert resolve_source_group([cash_row(dividCashPsBeforeTax="")])["state"] == "gross-source-consistent"


@pytest.mark.parametrize("field,value", [("dividCashPsBeforeTax", "0.7"), ("dividStocksPs", "0.1"),
                                         ("dividReserveToStockPs", "Infinity"), ("dividCashPsBeforeTax", "-0.6")])
def test_nonblank_numbers_must_be_finite_nonnegative_and_agree(field, value):
    assert resolve_source_group([cash_row(**{field: value})])["state"] == "unresolved"


@pytest.mark.parametrize("field,value", [("dividPlanDate", ""), ("dividRegistDate", "2021-07-01"),
                                         ("dividPlanDate", "2021-07-02"), ("dividPayDate", ""),
                                         ("dividPayDate", "2021-06-30"), ("dividOperateDate", "20210701")])
def test_missing_or_impossible_source_dates_fail_closed(field, value):
    assert resolve_source_group([cash_row(**{field: value})])["state"] == "unresolved"


def test_positive_shares_cannot_guess_listing_date():
    result = resolve_source_group([cash_row(dividCashStock="10转4派6元（含税）")])
    assert result["reason"] == "missing_or_invalid_date:dividStockMarketDate"


def test_decimal_plan_preserves_small_and_fractional_rates():
    terms = parse_complete_plan("10转4.9派0.0048元（含税）")
    assert terms["reserve_per_share"] == Decimal("0.49")
    assert terms["gross_cash_per_share"] == Decimal("0.00048")


@pytest.mark.parametrize("rows", [[], [{"code": "sh.600000"}, {}], [{"code": None}]])
def test_invalid_group_schema_does_not_emit_terms(rows):
    assert resolve_source_group(rows)["state"] == "unresolved"


@pytest.mark.parametrize("legs", list(permutations(("送2股", "转增1股", "派0.4元"))))
def test_named_leg_order_does_not_change_economics(legs):
    actual = parse_complete_plan("10" + "".join(legs) + "（含税）")
    expected = parse_complete_plan("10送2转1派0.4元（含税）")
    assert actual == expected


@pytest.mark.parametrize("description", ["10送1送2派6元", "10转1转增2派6元", "10派3元派3元",
                                         "10转1送2派0.4", "10转1元送2派0.4元"])
def test_repeated_or_incomplete_named_legs_are_not_merged(description):
    assert resolve_source_group([cash_row(dividCashStock=description)])["state"] == "unresolved"


@pytest.mark.parametrize("description,bonus,reserve", [("10转1送2派0.4元（含税）", "0.2", "0.1"),
                                                     ("10转1.5送0.5派0.4元（含税）", "0.05", "0.15")])
def test_observed_reserve_before_bonus_form_has_explicit_matching_legs(description, bonus, reserve):
    row = cash_row(dividCashStock=description, dividCashPsBeforeTax="0.04", dividStocksPs=bonus,
                   dividReserveToStockPs=reserve, dividStockMarketDate="2021-07-02")
    result = resolve_source_group([row])
    assert result["state"] == "gross-source-consistent"
    assert result["terms"]["bonus_per_share"] == bonus and result["terms"]["reserve_per_share"] == reserve
    assert result["ledgerReady"] is False


def test_tiny_rounding_and_large_document_conflicts_still_fail_exact_agreement():
    cash = cash_row(dividCashPsBeforeTax="0.91", dividCashStock="10派6.6元（含税）")
    reserve = cash_row(dividCashPsBeforeTax="0.324998", dividCashStock="10转3.999976派3.24998元（含税）",
                       dividReserveToStockPs="0.399998", dividStockMarketDate="2021-07-02")
    assert resolve_source_group([cash])["reason"] == "numeric_plan_conflict:dividCashPsBeforeTax"
    assert resolve_source_group([reserve])["reason"] == "numeric_plan_conflict:dividReserveToStockPs"
