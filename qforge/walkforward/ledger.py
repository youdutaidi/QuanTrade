"""Single owner of a local paper account's cash, shares and event lifecycle."""

from __future__ import annotations

import copy
from dataclasses import asdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .execution import decide_fill
from .models import Distribution, OpeningQuote, OrderIntent, Position


class PaperAccount:
    def __init__(self, policy: dict, sessions: list[str], prior_session: str | None = None):
        if not sessions or sessions != sorted(set(sessions)):
            raise ValueError("sessions must be nonempty, ordered and unique")
        for value in sessions + ([prior_session] if prior_session else []):
            _canonical_date(value)
        if prior_session and prior_session >= sessions[0]:
            raise ValueError("signal anchor must precede the first session")
        self._policy = copy.deepcopy(policy)
        self.sessions, self.previous = tuple(sessions), prior_session
        self._cash = _money(policy["initial_cash_cny"])
        if self._cash <= 0:
            raise ValueError("initial cash must be positive")
        self._positions: dict[str, Position] = {}
        self._claims: dict[str, dict] = {}
        self._events: list[dict] = []
        self._order_ids: set[str] = set()
        self._action_ids: set[str] = set()
        self._index, self._phase, self.today = -1, "closed", None
        self._emit("initial", cash=float(self._cash), sessions=sessions, prior_session=prior_session, policy=self._policy)

    @property
    def cash(self) -> Decimal:
        return self._cash

    @property
    def events(self) -> list[dict]:
        return copy.deepcopy(self._events)

    @property
    def positions(self) -> dict[str, Position]:
        return copy.deepcopy(self._positions)

    @property
    def economic_shares(self) -> dict[str, int]:
        return {code: pos.quantity + self._pending_shares(code) for code, pos in self._positions.items()
                if pos.quantity or self._pending_shares(code)}

    def begin_session(self, trade_date: str) -> None:
        if self._phase != "closed" or self._index + 1 >= len(self.sessions) or trade_date != self.sessions[self._index + 1]:
            raise ValueError("sessions must advance one at a time after closing")
        if not self._policy["supported_dates"][0] <= trade_date <= self._policy["supported_dates"][1]:
            raise ValueError("session outside the verified execution rule window")
        self._index += 1
        self._positions = {code: position for code, position in self._positions.items()
                           if position.quantity or self._pending_shares(code)}
        self.today, self._phase = trade_date, "open"
        self._ordered_symbols, self._action_references = set(), {}
        self._buy_seen = False
        self._record_quantities = {code: pos.quantity for code, pos in self._positions.items()}
        for position in self._positions.values():
            position.available = position.quantity
        self._emit("session_open")
        self._release_shares()

    def book_distribution(self, action: Distribution) -> None:
        if self._phase != "open" or self._ordered_symbols:
            raise ValueError("distributions must be booked before opening orders")
        if action.event_id in self._action_ids or action.symbol in self._action_references:
            raise ValueError("duplicate distribution; combine same-day events explicitly")
        if action.ex_date != self.today or action.record_date != self.previous:
            raise ValueError("distribution requires the preceding recorded ownership date")
        quantity = self._record_quantities.get(action.symbol, 0)
        cash, shares = _distribution_entitlement(action, quantity)
        self._claims[action.event_id] = {"action": action, "cash": cash, "shares": shares}
        self._action_ids.add(action.event_id)
        self._action_references[action.symbol] = action.official_reference_price
        self._emit("distribution", action=asdict(action), entitled_quantity=quantity,
                   cash_receivable=float(cash), shares_receivable=shares)
        self._release_shares()

    def execute(self, order: OrderIntent, quote: OpeningQuote) -> dict:
        if self._phase != "open" or order.execution_date != self.today or order.signal_date != self.previous:
            raise ValueError("order must use the preceding session signal at this session open")
        if not order.order_id or order.order_id in self._order_ids or order.symbol in self._ordered_symbols:
            raise ValueError("duplicate order ID or more than one order per symbol/session")
        if order.side == "SELL" and self._buy_seen:
            raise ValueError("opening sell orders must precede all buy orders")
        self._check_reference(order.symbol, quote.preclose)
        position = self._positions.get(order.symbol, Position())
        decision = decide_fill(order, quote, self._cash, position.available, self._policy)
        self._order_ids.add(order.order_id)
        self._ordered_symbols.add(order.symbol)
        self._buy_seen = self._buy_seen or order.side == "BUY"
        if decision.quantity:
            self._apply_fill(order, decision)
        self._emit("order", order=asdict(order), quote=asdict(quote), fill=asdict(decision))
        return asdict(decision)

    def validate_opening_references(self, references: dict[str, float]) -> None:
        if self._phase != "open" or self._ordered_symbols:
            raise ValueError("opening reference validation must precede orders")
        for symbol, quantity in self._record_quantities.items():
            if quantity:
                self._check_reference(symbol, references.get(symbol))

    def close_session(self, close_prices: dict[str, float], reference_prices: dict[str, float]) -> dict:
        if self._phase != "open":
            raise ValueError("session is not open")
        marks, stale, market_value = {}, [], Decimal(0)
        for symbol, position in self._positions.items():
            quantity = position.quantity + self._pending_shares(symbol)
            if not quantity:
                continue
            self._check_reference(symbol, reference_prices.get(symbol))
            price = close_prices.get(symbol, self._action_references.get(symbol, position.last_price))
            if price is None or _decimal(price) <= 0:
                raise ValueError(f"missing or invalid valuation price for {symbol}")
            if symbol not in close_prices:
                stale.append(symbol)
            marks[symbol] = float(price)
            market_value += _decimal(price) * quantity
        for symbol, price in marks.items():
            self._positions[symbol].last_price = price
        self._pay_cash()
        receivable = sum((claim["cash"] for claim in self._claims.values()), Decimal(0))
        snapshot = {"cash": float(self._cash), "cashReceivable": float(receivable),
                    "marketValue": float(market_value), "equity": float(self._cash + receivable + market_value),
                    "positions": {code: asdict(pos) for code, pos in self._positions.items()},
                    "pendingShares": {code: self._pending_shares(code) for code in self._positions}, "stalePrices": stale}
        self._emit("session_close", marks=marks, reference_prices=reference_prices, snapshot=snapshot)
        self._claims = {key: claim for key, claim in self._claims.items() if claim["cash"] or claim["shares"]}
        self._phase, self.previous = "closed", self.today
        return copy.deepcopy(snapshot)

    def _apply_fill(self, order, decision) -> None:
        position = self._positions.setdefault(order.symbol, Position())
        gross = _decimal(decision.price) * decision.quantity
        fees = sum((_decimal(value) for value in [decision.commission, decision.stamp_duty, decision.transfer_fee]), Decimal(0))
        if order.side == "BUY":
            self._cash -= gross + fees
            position.quantity += decision.quantity
        else:
            self._cash += gross - fees
            position.quantity -= decision.quantity
            position.available -= decision.quantity
        if self._cash < 0 or position.quantity < 0 or position.available < 0:
            raise ArithmeticError("negative cash or inventory after fill")
        if position.last_price is None:
            position.last_price = decision.price

    def _release_shares(self) -> None:
        for event_id, claim in self._claims.items():
            action = claim["action"]
            if claim["shares"] and action.shares_listing_date <= self.today:
                position = self._positions.setdefault(action.symbol, Position())
                position.quantity += claim["shares"]
                position.available += claim["shares"]
                self._emit("shares_released", event_id=event_id, quantity=claim["shares"])
                claim["shares"] = 0

    def _pay_cash(self) -> None:
        for event_id, claim in self._claims.items():
            if claim["cash"] and claim["action"].payment_date <= self.today:
                self._cash += claim["cash"]
                self._emit("cash_paid", event_id=event_id, amount=float(claim["cash"]))
                claim["cash"] = Decimal(0)

    def _pending_shares(self, symbol: str) -> int:
        return sum(claim["shares"] for claim in self._claims.values() if claim["action"].symbol == symbol)

    def _check_reference(self, symbol: str, preclose: float | None) -> None:
        if not self._record_quantities.get(symbol):
            return
        expected = self._action_references.get(symbol, self._positions[symbol].last_price)
        if preclose is None or expected is None or abs(_decimal(preclose) - _decimal(expected)) > Decimal("0.01"):
            raise ValueError(f"unresolved reference-price change or missing corporate action for {symbol}")

    def _emit(self, kind: str, **details) -> None:
        self._events.append({"sequence": len(self._events), "date": self.today, "kind": kind, **details})


def _distribution_entitlement(action: Distribution, quantity: int) -> tuple[Decimal, int]:
    if quantity <= 0 or not action.event_id or not action.evidence_id or not action.tax_basis:
        raise ValueError("distribution requires recorded ownership, evidence and an explicit tax basis")
    for value in [action.record_date, action.ex_date, action.payment_date, action.shares_listing_date]:
        if value is not None:
            _canonical_date(value)
    cash_rate, share_rate = _decimal(action.net_cash_per_share), _decimal(action.new_shares_per_share)
    if cash_rate < 0 or share_rate < 0 or _decimal(action.official_reference_price) <= 0:
        raise ValueError("invalid distribution amounts or reference price")
    if cash_rate and (not action.payment_date or action.payment_date < action.ex_date):
        raise ValueError("cash payment date must not precede ex-date")
    if share_rate and (not action.shares_listing_date or action.shares_listing_date < action.ex_date):
        raise ValueError("share listing date must not precede ex-date")
    shares = quantity * share_rate
    if shares != shares.to_integral_value():
        raise ValueError("fractional bonus-share allocation requires explicit settlement evidence")
    return _money(quantity * cash_rate), int(shares)


def _decimal(value) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("nonfinite monetary or share value")
    return result


def _money(value) -> Decimal:
    return _decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _canonical_date(value: str) -> None:
    if date.fromisoformat(value).isoformat() != value:
        raise ValueError("ledger dates must use YYYY-MM-DD")
