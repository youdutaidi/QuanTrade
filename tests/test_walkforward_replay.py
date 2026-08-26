import copy
from pathlib import Path

import pandas as pd
import pytest

from qforge.walkforward.ledger import PaperAccount
from qforge.walkforward.ledger_audit import audit_ledger
from qforge.walkforward.metrics import period_metrics
from qforge.walkforward.models import Distribution, OpeningQuote, OrderIntent
from qforge.walkforward.replay import ReplayFailure, replay_candidate
from qforge.walkforward.replay_inputs import build_score_cache, prepare_replay_inputs, signal_key
from qforge.walkforward.specification import StudySpec
from qforge.walkforward.synthetic_market import synthetic_market


@pytest.fixture(scope="module")
def scene():
    spec = StudySpec.from_json(Path(__file__).resolve().parents[1] / "configs/walk_forward.json")
    frame, days, securities, actions = synthetic_market(spec)
    inputs = prepare_replay_inputs(frame, days, securities, spec)
    cache = build_score_cache(inputs, spec)
    candidate = next(item for item in spec.candidates() if item.family == "short_reversal" and
                     item.lookback == 5 and item.rebalance_days == 5 and item.top_n == 10)
    return spec, frame, days, securities, actions, inputs, cache, candidate


def run_scene(scene, end_index=419, actions_override=None):
    spec, _, days, _, actions, inputs, cache, candidate = scene
    return replay_candidate(inputs, cache[signal_key(candidate)], candidate, spec, days[400], days[end_index],
                            actions if actions_override is None else actions_override)


def test_factor_to_account_first_day_fees_and_scheduled_intents(scene):
    spec, frame, days, _, _, _, _, candidate = scene
    result = run_scene(scene)
    assert [row["date"] for row in result["decisions"]] == [days[index] for index in (400, 405, 410, 415)]
    first = result["decisions"][0]
    assert first["signalDate"] == days[399]
    assert first["targets"] == {code: 0.1 for code in ("sh.600000", "sz.000001", "sz.300001")}
    for order in first["orders"]:
        reference = first["referencePrices"][order["symbol"]]
        assert order["quantity"] == int(100000 / reference)
    pnl = 0.0
    for event in result["events"]:
        if event["kind"] == "order" and event["date"] == days[400]:
            code, fill = event["order"]["symbol"], event["fill"]
            close = frame.loc[(frame["symbol"] == code) & frame["date"].eq(days[400]), "raw_close"].iloc[0]
            pnl += fill["quantity"] * (close - fill["price"]) - sum(fill[key] for key in ("commission", "stamp_duty", "transfer_fee"))
    assert result["snapshots"][0]["equity"] == pytest.approx(1000000 + pnl, abs=1e-7)
    assert result["metrics"]["annualizedReturn"] is None
    assert audit_ledger(result["events"], spec.values["execution"])["allPass"]
    assert result["verifiedStrategy"] is False


def test_pending_bonus_shares_are_included_in_rebalance_exposure(scene):
    result = run_scene(scene)
    old_quantity = result["snapshots"][4]["positions"]["sh.600000"]["quantity"]
    assert result["decisions"][1]["economicShares"]["sh.600000"] == old_quantity + int(old_quantity * 0.1)
    assert result["snapshots"][5]["pendingShares"]["sh.600000"] == int(old_quantity * 0.1)
    assert result["snapshots"][6]["cashReceivable"] > 0
    assert result["snapshots"][7]["cashReceivable"] == 0


def test_actual_open_does_not_size_orders_and_same_day_volume_does_not_set_capacity(scene):
    spec, frame, days, securities, actions, _, _, candidate = scene
    changed = frame.copy()
    mask = changed["date"].eq(days[400]) & changed["symbol"].ne(spec.values["benchmark"])
    changed.loc[mask, "raw_open"] *= 1.03
    changed.loc[mask, "volume"] *= 1000
    inputs = prepare_replay_inputs(changed, days, securities, spec)
    cache = build_score_cache(inputs, spec)
    altered = replay_candidate(inputs, cache[signal_key(candidate)], candidate, spec, days[400], days[400], actions)
    baseline = run_scene(scene, end_index=400)
    assert altered["decisions"] == baseline["decisions"]
    original = [row["quote"]["capacity"] for row in baseline["events"] if row["kind"] == "order"]
    assert [row["quote"]["capacity"] for row in altered["events"] if row["kind"] == "order"] == original


def test_future_prices_cannot_change_an_earlier_execution_prefix(scene):
    spec, frame, days, securities, actions, _, _, candidate = scene
    changed = frame.copy()
    future = changed["date"].ge(days[410])
    changed.loc[future, ["close", "raw_open", "raw_close", "raw_preclose", "volume", "amount"]] *= 1.07
    inputs = prepare_replay_inputs(changed, days, securities, spec)
    cache = build_score_cache(inputs, spec)
    result = replay_candidate(inputs, cache[signal_key(candidate)], candidate, spec, days[400], days[409], actions)
    baseline = run_scene(scene, end_index=409)
    assert result["events"] == baseline["events"]
    assert result["decisions"] == baseline["decisions"]


def test_missing_listed_bar_is_not_forward_filled(scene):
    spec, frame, days, securities, *_ = scene
    with pytest.raises(ValueError, match="missing listed bar"):
        prepare_replay_inputs(frame.drop(frame.index[400]), days, securities, spec)


def test_missing_distribution_preserves_failure_evidence_without_metrics(scene):
    with pytest.raises(ReplayFailure, match="reference-price change") as failure:
        run_scene(scene, actions_override=())
    assert failure.value.failed_date == scene[2][405]
    assert failure.value.events[-1]["kind"] == "session_open"
    assert all(row["date"] < scene[2][405] for row in failure.value.decisions)


def test_failure_after_planning_retains_the_requested_orders(scene):
    spec, _, days, _, actions, inputs, cache, candidate = scene
    corrupted = copy.deepcopy(inputs)
    corrupted.fields["is_st"].loc[days[400], "sh.600000"] = 2
    with pytest.raises(ReplayFailure, match="missing listed opening quote") as failure:
        replay_candidate(corrupted, cache[signal_key(candidate)], candidate, spec, days[400], days[-1], actions)
    assert failure.value.decisions[-1]["date"] == days[400]
    assert failure.value.decisions[-1]["orders"]


def test_held_delisting_cannot_be_marked_forever_at_its_last_price(scene):
    spec, frame, days, securities, actions, _, _, candidate = scene
    master = securities.copy()
    master.loc[master["code"].eq("sh.600000"), "out_date"] = days[410]
    subset = frame[~(frame["symbol"].eq("sh.600000") & frame["date"].ge(days[410]))]
    inputs = prepare_replay_inputs(subset, days, master, spec)
    cache = build_score_cache(inputs, spec)
    with pytest.raises(ReplayFailure, match="held delisting") as failure:
        replay_candidate(inputs, cache[signal_key(candidate)], candidate, spec, days[400], days[-1], actions)
    assert failure.value.events[-1]["date"] == days[409]


def test_all_frozen_candidates_replay_without_changing_the_grid(scene):
    spec, _, days, _, actions, inputs, cache, _ = scene
    assert len(cache) == 16 and len(spec.candidates()) == 144
    for candidate in spec.candidates():
        result = replay_candidate(inputs, cache[signal_key(candidate)], candidate, spec, days[400], days[-1], actions)
        audit = audit_ledger(result["events"], spec.values["execution"])
        assert audit["allPass"] and audit["allSessionsClosed"], (candidate, audit)


def test_metrics_include_initial_entry_loss_and_do_not_annualize_short_samples():
    result = period_metrics(pd.Series([999.0], index=pd.to_datetime(["2025-01-02"])), 1000, "2025-01-02", "2025-01-02")
    assert result["totalReturn"] == pytest.approx(-0.001)
    assert result["maxDrawdown"] == pytest.approx(-0.001)
    assert result["annualizedReturn"] is None and result["sharpe"] is None


def test_zero_positions_pruned_next_session_without_changing_prior_snapshots(scene):
    policy = scene[0].values["execution"]
    days = ["2026-07-01", "2026-07-02", "2026-07-03"]
    account = PaperAccount(policy, days, "2026-06-30")
    for index, side in enumerate(("BUY", "SELL")):
        account.begin_session(days[index])
        prior = "2026-06-30" if index == 0 else days[index - 1]
        account.execute(OrderIntent(side, "sh.600000", side, 1000, prior, days[index]),
                        OpeningQuote("sh.600000", days[index], 10, 10, False, True, 10000, prior))
        old = account.close_session({"sh.600000": 10}, {"sh.600000": 10})
    assert old["positions"]["sh.600000"]["quantity"] == 0
    account.begin_session(days[2])
    assert account.positions == account.economic_shares == {}
    account.close_session({}, {})
    assert old["positions"]["sh.600000"]["quantity"] == 0
    assert audit_ledger(account.events, policy)["allPass"]


def test_zero_ordinary_position_retains_unlisted_bonus_shares(scene):
    policy, code = scene[0].values["execution"], "sh.600000"
    days = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06"]
    account = PaperAccount(policy, days, "2026-06-30")
    account.begin_session(days[0])
    account.execute(OrderIntent("buy", code, "BUY", 1000, "2026-06-30", days[0]),
                    OpeningQuote(code, days[0], 10, 10, False, True, 10000, "2026-06-30"))
    account.close_session({code: 10}, {code: 10})
    account.begin_session(days[1])
    account.book_distribution(Distribution("pending", code, days[0], days[1], 0.16, 0.1,
                                          days[3], days[3], 8.91, "synthetic", "explicit synthetic net cash"))
    account.execute(OrderIntent("sell-ordinary", code, "SELL", 1000, days[0], days[1]),
                    OpeningQuote(code, days[1], 8.91, 8.91, False, True, 10000, days[0]))
    account.close_session({code: 8.91}, {code: 8.91})
    account.begin_session(days[2])
    assert account.positions[code].quantity == 0 and account.economic_shares[code] == 100
    account.close_session({code: 8.91}, {code: 8.91})
    account.begin_session(days[3])
    assert account.positions[code].quantity == account.positions[code].available == 100
    final = account.close_session({code: 8.91}, {code: 8.91})
    assert final["cashReceivable"] == 0
    assert audit_ledger(account.events, policy)["allPass"]
