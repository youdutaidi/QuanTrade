"""Scheduled portfolio execution; PaperAccount remains the sole balance owner."""

from __future__ import annotations

import math
from dataclasses import asdict

import pandas as pd

from .ledger import PaperAccount
from .metrics import period_metrics
from .models import Distribution, OpeningQuote
from .orders import plan_rebalance
from .replay_inputs import ReplayInputs
from .specification import Candidate, StudySpec


class ReplayFailure(RuntimeError):
    """Retain partial evidence; failed candidates must not silently receive metrics."""
    def __init__(self, candidate: str, day: str, cause: Exception, events: list, decisions: list):
        super().__init__(f"{candidate} stopped on {day}: {cause}")
        self.candidate_id, self.failed_date = candidate, day
        self.events, self.decisions = events, decisions


def replay_candidate(inputs: ReplayInputs, scores: pd.DataFrame, candidate: Candidate, spec: StudySpec,
                     start: str, end: str, actions: tuple[Distribution, ...] = ()) -> dict:
    sessions, prior = _evaluation_sessions(inputs, scores, candidate, spec, start, end)
    policy = spec.values["execution"]
    account = PaperAccount(policy, sessions, prior)
    equity, decisions, snapshots = float(account.cash), [], []
    by_date = {}
    for action in actions:
        by_date.setdefault(action.ex_date, []).append(action)
    for index, day in enumerate(sessions):
        try:
            previous = prior if index == 0 else sessions[index - 1]
            _begin(account, inputs, day, by_date.get(day, []))
            if index % candidate.rebalance_days == 0:
                _rebalance(account, inputs, scores, candidate, policy, previous, day, equity, decisions)
            snapshot = _close(account, inputs, day)
            snapshots.append({"date": day, **snapshot})
            equity = snapshot["equity"]
        except (ValueError, TypeError, KeyError, ArithmeticError) as error:
            raise ReplayFailure(candidate.candidate_id, day, error, account.events, decisions) from error
    curve = pd.Series([row["equity"] for row in snapshots], index=pd.to_datetime(sessions))
    return {"candidateId": candidate.candidate_id, "events": account.events, "decisions": decisions,
            "snapshots": snapshots, "metrics": period_metrics(curve, policy["initial_cash_cny"], start, end),
            "maxObservedStockWeight": max(_concentration(row) for row in snapshots),
            "staleValuationSessions": sum(bool(row["stalePrices"]) for row in snapshots),
            "verifiedStrategy": False, "scope": "daily opening-price proxy; source, action and statistical admission remain separate"}


def _evaluation_sessions(inputs, scores, candidate, spec, start, end):
    if candidate not in spec.candidates() or start > end:
        raise ValueError("candidate or replay window is outside the frozen specification")
    if not scores.index.equals(inputs.returns.index) or not scores.columns.equals(inputs.returns.columns):
        raise ValueError("score axes do not match replay inputs")
    sessions = [day for day in inputs.sessions if start <= day <= end]
    if not sessions or inputs.sessions.index(sessions[0]) == 0:
        raise ValueError("evaluation needs sessions and a preceding completed signal session")
    return sessions, inputs.sessions[inputs.sessions.index(sessions[0]) - 1]


def _begin(account, inputs, day, actions):
    prior = {code: position.quantity for code, position in account.positions.items()}
    for code in account.economic_shares:
        if not bool(inputs.listed.loc[day, code]):
            raise ValueError(f"held delisting requires explicit settlement evidence: {code}")
    account.begin_session(day)
    for action in actions:
        if prior.get(action.symbol, 0):
            account.book_distribution(action)
    account.validate_opening_references(inputs.fields["raw_preclose"].loc[day].to_dict())


def _rebalance(account, inputs, scores, candidate, policy, previous, day, equity, decisions):
    available_scores = scores.loc[previous].where(inputs.eligible.loc[previous])
    references = inputs.fields["raw_preclose"].loc[day].to_dict()
    shares = account.economic_shares
    plan = plan_rebalance(candidate, available_scores, equity, shares, references,
                          previous, day, policy["max_stock_weight"])
    decision = {"date": day, "signalDate": previous, "equityBasis": equity,
                "targets": plan.target_weights, "economicShares": shares, "desiredShares": plan.desired_shares,
                "referencePrices": {code: references[code] for code in plan.desired_shares},
                "orders": [asdict(order) for order in plan.orders],
                "sizingBasis": "prior-close equity and pre-opening reference, never actual open/close"}
    decisions.append(decision)
    for order in plan.orders:
        account.execute(order, _quote(inputs, order.symbol, day))


def _quote(inputs: ReplayInputs, code: str, day: str) -> OpeningQuote:
    status, st = (inputs.fields[field].loc[day, code] for field in ("trade_status", "is_st"))
    if not inputs.listed.loc[day, code] or status not in (0, 1) or st not in (0, 1) or inputs.capacity_asof[day] is None:
        raise ValueError("missing listed opening quote, status or past capacity timestamp")
    opening = inputs.fields["raw_open"].loc[day, code]
    return OpeningQuote(code, day, float(opening) if pd.notna(opening) else None,
                        float(inputs.fields["raw_preclose"].loc[day, code]), bool(st), bool(status),
                        int(inputs.capacity.loc[day, code]), inputs.capacity_asof[day])


def _close(account, inputs, day):
    prices, references = {}, {}
    for code in account.economic_shares:
        close = inputs.fields["raw_close"].loc[day, code]
        if pd.notna(close) and math.isfinite(close) and close > 0:
            prices[code] = float(close)
        reference = inputs.fields["raw_preclose"].loc[day, code]
        references[code] = float(reference) if pd.notna(reference) else None
    return account.close_session(prices, references)


def _concentration(snapshot: dict) -> float:
    weights = []
    for code, position in snapshot["positions"].items():
        quantity = position["quantity"] + snapshot["pendingShares"].get(code, 0)
        if quantity:
            weights.append(quantity * position["last_price"] / snapshot["equity"])
    return max(weights, default=0.0)
