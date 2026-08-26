from __future__ import annotations

import copy
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from qforge.walkforward.ledger import PaperAccount
from qforge.walkforward.ledger_audit import audit_ledger
from qforge.walkforward.models import Distribution, OpeningQuote, OrderIntent
from qforge.walkforward.specification import StudySpec


CODE = "sh.600000"
DAYS = ["2026-07-01", "2026-07-02", "2026-07-03"]


@pytest.fixture
def policy():
    return StudySpec.from_json(Path(__file__).resolve().parents[1] / "configs/walk_forward.json").values["execution"]


def buy_first_day(account, quantity=1000):
    account.begin_session(DAYS[0])
    order = OrderIntent("buy", CODE, "BUY", quantity, "2026-06-30", DAYS[0])
    quote = OpeningQuote(CODE, DAYS[0], 10, 10, False, True, 10000, "2026-06-30")
    return account.execute(order, quote)


def action():
    return Distribution("distribution-1", CODE, DAYS[0], DAYS[1], 0.16, 0.1, DAYS[2], DAYS[2], 8.91,
                        "synthetic-fixture", "explicit synthetic net cash; not an investor tax determination")


def three_session_account(policy):
    account = PaperAccount(policy, DAYS, "2026-06-30")
    buy_first_day(account)
    first = account.close_session({CODE: 10}, {CODE: 10})
    account.begin_session(DAYS[1])
    account.book_distribution(action())
    second = account.close_session({CODE: 8.91}, {CODE: 8.91})
    account.begin_session(DAYS[2])
    order = OrderIntent("sell", CODE, "SELL", 1100, DAYS[1], DAYS[2])
    quote = OpeningQuote(CODE, DAYS[2], 9, 8.91, False, True, 10000, DAYS[1])
    account.execute(order, quote)
    last = account.close_session({}, {CODE: 8.91})
    return account, [first, second, last]


def test_hand_calculated_dividend_bonus_share_and_fee_ledger(policy):
    account, snapshots = three_session_account(policy)
    assert snapshots[0]["equity"] == pytest.approx(999984.90)
    assert snapshots[0]["positions"][CODE]["available"] == 0
    assert snapshots[1]["cash"] == pytest.approx(989984.90)
    assert snapshots[1]["cashReceivable"] == 160
    assert snapshots[1]["pendingShares"][CODE] == 100
    assert snapshots[1]["positions"][CODE]["available"] == 1000
    assert snapshots[1]["equity"] == pytest.approx(999945.90)
    assert snapshots[2]["cash"] == pytest.approx(1000023.86)
    assert snapshots[2]["cashReceivable"] == snapshots[2]["marketValue"] == 0
    assert snapshots[2]["positions"][CODE]["quantity"] == 0
    replay = audit_ledger(account.events, policy)
    assert replay["allPass"], replay
    assert replay["finalEquity"] == pytest.approx(1000023.86)


def test_affordability_includes_minimum_commission_and_transfer(policy):
    policy["initial_cash_cny"] = 1006.01
    account = PaperAccount(policy, DAYS, "2026-06-30")
    fill = buy_first_day(account, 200)
    assert fill["quantity"] == 100 and account.cash == Decimal("0.00")
    assert account.positions[CODE].available == 0


def test_dividend_payable_today_is_not_available_until_close(policy):
    policy["initial_cash_cny"] = 10015.10
    account = PaperAccount(policy, DAYS, "2026-06-30")
    buy_first_day(account)
    account.close_session({CODE: 10}, {CODE: 10})
    account.begin_session(DAYS[1])
    account.book_distribution(replace(action(), net_cash_per_share=1.1, new_shares_per_share=0,
                                      payment_date=DAYS[1], shares_listing_date=None, official_reference_price=8.9))
    order = OrderIntent("extra-buy", CODE, "BUY", 100, DAYS[0], DAYS[1])
    quote = OpeningQuote(CODE, DAYS[1], 8.9, 8.9, False, True, 1000, DAYS[0])
    assert account.execute(order, quote)["quantity"] == 0
    assert account.cash == 0
    snapshot = account.close_session({CODE: 8.9}, {CODE: 8.9})
    assert snapshot["cash"] == 1100 and snapshot["cashReceivable"] == 0
    assert audit_ledger(account.events, policy)["allPass"]


def test_t_plus_one_rollover_and_duplicate_session_orders(policy):
    account = PaperAccount(policy, DAYS, "2026-06-30")
    buy_first_day(account)
    assert account.positions[CODE].quantity == 1000 and account.positions[CODE].available == 0
    with pytest.raises(ValueError, match="one order"):
        account.execute(OrderIntent("again", CODE, "SELL", 1000, "2026-06-30", DAYS[0]),
                        OpeningQuote(CODE, DAYS[0], 10, 10, False, True, 1000, "2026-06-30"))
    account.close_session({CODE: 10}, {CODE: 10})
    account.begin_session(DAYS[1])
    assert account.positions[CODE].available == 1000


def test_unresolved_corporate_action_cannot_generate_an_equity_curve(policy):
    account = PaperAccount(policy, DAYS, "2026-06-30")
    buy_first_day(account)
    account.close_session({CODE: 10}, {CODE: 10})
    account.begin_session(DAYS[1])
    with pytest.raises(ValueError, match="corporate action"):
        account.close_session({CODE: 8.91}, {CODE: 8.91})
    assert account.events[-1]["kind"] == "session_open"


def test_missing_close_is_carried_and_flagged_not_zeroed(policy):
    account = PaperAccount(policy, DAYS, "2026-06-30")
    buy_first_day(account)
    account.close_session({CODE: 10}, {CODE: 10})
    account.begin_session(DAYS[1])
    snapshot = account.close_session({}, {CODE: 10})
    assert snapshot["marketValue"] == 10000 and snapshot["stalePrices"] == [CODE]
    assert audit_ledger(account.events, policy)["allPass"]


def test_suspended_ex_date_uses_official_reference_for_stale_mark(policy):
    account = PaperAccount(policy, DAYS, "2026-06-30")
    buy_first_day(account)
    account.close_session({CODE: 10}, {CODE: 10})
    account.begin_session(DAYS[1])
    account.book_distribution(action())
    snapshot = account.close_session({}, {CODE: 8.91})
    assert snapshot["marketValue"] == 9801 and snapshot["stalePrices"] == [CODE]


def test_missing_evidence_fractional_allocations_and_duplicates_rejected(policy):
    account = PaperAccount(policy, DAYS, "2026-06-30")
    buy_first_day(account)
    account.close_session({CODE: 10}, {CODE: 10})
    account.begin_session(DAYS[1])
    for broken in [replace(action(), evidence_id=""), replace(action(), new_shares_per_share=0.0005)]:
        with pytest.raises(ValueError):
            account.book_distribution(broken)
    account.book_distribution(action())
    with pytest.raises(ValueError, match="duplicate"):
        account.book_distribution(action())


@pytest.mark.parametrize("corruption", ["fee", "quantity", "equity", "payment", "ownership", "sequence"])
def test_independent_witness_detects_tampered_events(policy, corruption):
    account, _ = three_session_account(policy)
    events = account.events
    if corruption in {"fee", "quantity"}:
        event = next(row for row in events if row["kind"] == "order")
        event["fill"]["commission" if corruption == "fee" else "quantity"] += 1
    elif corruption == "equity":
        events[-1]["snapshot"]["equity"] += 100000
    elif corruption == "payment":
        next(row for row in events if row["kind"] == "cash_paid")["amount"] += 1
    elif corruption == "ownership":
        next(row for row in events if row["kind"] == "distribution")["entitled_quantity"] += 100
    else:
        events[-1]["sequence"] += 1
    assert not audit_ledger(events, policy)["allPass"]
    assert audit_ledger(account.events, policy)["allPass"]  # Evidence export is a copy.


def test_policy_and_session_timing_cannot_change_silently(policy):
    account = PaperAccount(policy, DAYS, "2026-06-30")
    saved = copy.deepcopy(policy)
    policy["commission_rate"] = 0
    buy_first_day(account)
    with pytest.raises(ValueError, match="one at a time"):
        account.begin_session(DAYS[2])
    account.close_session({CODE: 10}, {CODE: 10})
    assert audit_ledger(account.events, saved)["allPass"]
    assert not audit_ledger(account.events, policy)["allPass"]
