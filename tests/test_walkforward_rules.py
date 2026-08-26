from __future__ import annotations

from pathlib import Path

import pytest

from qforge.walkforward.rules import board_for_symbol, execution_costs, normalize_quantity, opening_fill_price, price_limits
from qforge.walkforward.specification import StudySpec


@pytest.fixture
def policy():
    path = Path(__file__).resolve().parents[1] / "configs" / "walk_forward.json"
    return StudySpec.from_json(path).values["execution"]


def test_fee_boundaries_and_no_double_counting(policy):
    before = execution_costs("SELL", 100000, "2022-04-28", policy)
    after = execution_costs("SELL", 100000, "2022-04-29", policy)
    assert before.commission == after.commission == 30.0
    assert before.transfer_fee == 2 and after.transfer_fee == 1
    assert execution_costs("SELL", 100000, "2023-08-25", policy).stamp_duty == 100
    assert execution_costs("SELL", 100000, "2023-08-28", policy).stamp_duty == 50
    assert execution_costs("BUY", 100000, "2023-08-28", policy).stamp_duty == 0
    assert execution_costs("BUY", 100, "2026-08-24", policy).commission == 5
    assert execution_costs("BUY", 0, "2026-08-24", policy).total == 0


def test_fee_rounding_uses_decimal_half_up(policy):
    assert execution_costs("BUY", 100500, "2026-08-24", policy).transfer_fee == 1.01
    assert execution_costs("BUY", 50250, "2022-04-28", policy).transfer_fee == 1.01


def test_compact_iso_date_does_not_change_schedule_comparison(policy):
    assert price_limits("sh.600000", 10, "20260703", True, policy) == (9.5, 10.5)


def test_mainboard_st_rule_changes_only_at_effective_date(policy):
    for code in ["sh.600000", "sz.000001"]:
        assert price_limits(code, 10, "2026-07-03", True, policy) == (9.5, 10.5)
        assert price_limits(code, 10, "2026-07-06", True, policy) == (9.0, 11.0)
        assert price_limits(code, 10, "2026-07-03", False, policy) == (9.0, 11.0)
    for code in ["sh.688001", "sz.300001"]:
        assert price_limits(code, 10, "2020-08-25", True, policy) == (8.0, 12.0)


def test_exchange_half_up_price_rounding(policy):
    assert price_limits("sh.600000", 10.05, "2025-01-02", False, policy) == (9.05, 11.06)


def test_lots_star_one_share_steps_and_t_plus_one_available_inventory(policy):
    assert normalize_quantity("sh.600000", "BUY", 201, 0, 1000, policy) == 200
    assert normalize_quantity("sh.688001", "BUY", 199, 0, 1000, policy) == 0
    assert normalize_quantity("sh.688001", "BUY", 201, 0, 1000, policy) == 201
    assert normalize_quantity("sh.688001", "SELL", 199, 400, 1000, policy) == 0
    assert normalize_quantity("sh.688001", "SELL", 199, 199, 1000, policy) == 199
    assert normalize_quantity("sh.600000", "SELL", 1000, 0, 1000, policy) == 0
    assert normalize_quantity("sh.600000", "SELL", 1000, 215, 1000, policy) == 215
    assert normalize_quantity("sz.300001", "BUY", 500000, 0, 500000, policy) == 300000


def test_open_fill_rejects_adverse_limit_and_bounds_without_future_high_low_or_volume():
    assert opening_fill_price("BUY", 11, 9, 11, 10) is None
    assert opening_fill_price("SELL", 9, 9, 11, 10) is None
    assert opening_fill_price("BUY", 10.99, 9, 11, 10) is None
    assert opening_fill_price("BUY", 12, 9, 11, 10) is None
    assert opening_fill_price("BUY", 10.01, 9, 11, 10) == 10.03
    assert opening_fill_price("SELL", 10.01, 9, 11, 10) == 9.99


@pytest.mark.parametrize("code", ["sh.900901", "sz.200001", "sh.000300", "hk.00700", "sh.6000000"])
def test_unsupported_markets_indices_and_b_shares_rejected(code):
    with pytest.raises(ValueError):
        board_for_symbol(code)


def test_unknown_dates_invalid_sides_and_nonfinite_prices_rejected(policy):
    with pytest.raises(ValueError):
        execution_costs("SELL", 100, "2026-08-25", policy)
    with pytest.raises(ValueError):
        execution_costs("SHORT", 100, "2026-08-24", policy)
    with pytest.raises(ValueError):
        price_limits("sh.600000", float("nan"), "2026-08-24", False, policy)
