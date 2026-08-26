"""Read-only, independent arithmetic replay; not independent market-price proof.

This witness deliberately does not import the account, its execution helper or
fee functions. It reconstructs ownership and cash from persisted event inputs.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


def audit_ledger(events: list[dict], policy: dict) -> dict:
    state = {"positions": {}, "claims": {}, "cash": Decimal(0), "date": None, "previous": None,
             "index": -1, "phase": "closed", "order_ids": set(), "action_ids": set(), "snapshots": 0}
    handlers = {"initial": _initial, "session_open": _open, "order": _order, "distribution": _distribution,
                "shares_released": _release, "cash_paid": _payment, "session_close": _close}
    try:
        if not events or events[0]["kind"] != "initial":
            raise ValueError("ledger must begin with initial funding")
        for sequence, event in enumerate(events):
            if event["sequence"] != sequence or event["kind"] not in handlers:
                raise ValueError("event sequence or kind invalid")
            if event["kind"] not in {"initial", "session_open"} and event["date"] != state["date"]:
                raise ValueError("event date does not match open session")
            handlers[event["kind"]](state, event, policy)
            state["checked"] = sequence + 1
        if state["phase"] != "closed" or not state["snapshots"]:
            raise ValueError("ledger has no completed session")
    except (KeyError, ValueError, TypeError, IndexError, ArithmeticError) as error:
        return {"allPass": False, "error": str(error), "checkedEvents": state.get("checked", 0),
                "scope": "accounting replay only; source and strategy verification separate"}
    return {"allPass": True, "checkedEvents": len(events), "snapshots": state["snapshots"],
            "allSessionsClosed": state["snapshots"] == len(state["sessions"]),
            "finalCash": float(state["cash"]), "finalEquity": state["equity"],
            "scope": "accounting replay only; source and strategy verification separate"}


def _initial(state, event, policy):
    if event["sequence"] != 0 or event["policy"] != policy:
        raise ValueError("duplicate funding or execution policy mismatch")
    _equal(event["cash"], policy["initial_cash_cny"], "initial funding")
    state.update(cash=_decimal(event["cash"]), sessions=event["sessions"], previous=event["prior_session"])


def _open(state, event, policy):
    index = state["index"] + 1
    if state["phase"] != "closed" or index >= len(state["sessions"]) or event["date"] != state["sessions"][index]:
        raise ValueError("invalid session transition")
    state.update(index=index, date=event["date"], phase="open", bought=False, ordered=set(), references={}, closing=False)
    state["record_quantities"] = {code: row["quantity"] for code, row in state["positions"].items()}
    for position in state["positions"].values():
        position["available"] = position["quantity"]


def _order(state, event, policy):
    order, quote, fill = event["order"], event["quote"], event["fill"]
    symbol, side, quantity = order["symbol"], order["side"], fill["quantity"]
    if state["phase"] != "open" or state["closing"] or order["signal_date"] != state["previous"]:
        raise ValueError("order timing invalid")
    if order["execution_date"] != state["date"] or quote["trade_date"] != state["date"] or quote["symbol"] != symbol:
        raise ValueError("order/quote identity invalid")
    if quote["capacity_asof"] > order["signal_date"] or order["order_id"] in state["order_ids"] or symbol in state["ordered"]:
        raise ValueError("capacity lookahead or duplicate order")
    if side not in {"BUY", "SELL"} or side == "SELL" and state["bought"]:
        raise ValueError("side or sell-before-buy order invalid")
    _reference(state, symbol, quote["preclose"])
    if not isinstance(quantity, int) or quantity < 0 or quantity > min(order["quantity"], quote["capacity"]):
        raise ValueError("invalid fill quantity")
    state["order_ids"].add(order["order_id"])
    state["ordered"].add(symbol)
    state["bought"] = state["bought"] or side == "BUY"
    if quantity == 0:
        for key in ["price", "commission", "stamp_duty", "transfer_fee"]:
            _equal(fill[key], 0, "rejected order charged a cost")
        return
    position = state["positions"].setdefault(symbol, {"quantity": 0, "available": 0, "last_price": fill["price"]})
    _check_execution(order, quote, fill, position["available"], policy)
    fees = _fees(side, quantity * _decimal(fill["price"]), state["date"], policy)
    for name, value in fees.items():
        _equal(fill[name], value, f"incorrect {name}")
    gross = quantity * _decimal(fill["price"])
    direction = 1 if side == "BUY" else -1
    state["cash"] -= direction * gross + sum(fees.values())
    position["quantity"] += direction * quantity
    if side == "SELL":
        position["available"] -= quantity
    if state["cash"] < 0 or position["quantity"] < 0 or position["available"] < 0:
        raise ValueError("negative cash or T+1 inventory")


def _check_execution(order, quote, fill, available, policy):
    symbol, side, quantity = order["symbol"], order["side"], fill["quantity"]
    board = "star" if symbol.startswith("sh.68") else "chinext" if symbol.startswith("sz.30") else "main"
    rule = policy["board_rules"][board]
    if not quote["tradeable"] or side == "BUY" and quote["is_st"]:
        raise ValueError("nontradeable/ST buy filled")
    if quantity > rule["max_limit_order"] or side == "SELL" and quantity > available:
        raise ValueError("order cap or T+1 violation")
    full_exit = side == "SELL" and quantity == available
    if not full_exit and (quantity < rule["minimum"] or (quantity - rule["minimum"]) % rule["step"]):
        raise ValueError("invalid board lot")
    sign = 1 if side == "BUY" else -1
    raw = _decimal(quote["raw_open"])
    modeled = raw * (1 + sign * _decimal(policy["slippage_bps"]) / 10000)
    rounding = ROUND_CEILING if side == "BUY" else ROUND_FLOOR
    expected = modeled.quantize(Decimal("0.01"), rounding=rounding)
    _equal(fill["price"], expected, "slippage price mismatch")
    rate = _rate(policy["mainboard_st_limit"], quote["trade_date"]) if board == "main" and quote["is_st"] else _decimal(rule["price_limit"])
    reference = _decimal(quote["preclose"])
    lower, upper = _cents(reference * (1 - rate)), _cents(reference * (1 + rate))
    if not lower <= raw <= upper or not lower <= expected <= upper or side == "BUY" and raw == upper or side == "SELL" and raw == lower:
        raise ValueError("fill outside conservative opening bounds")


def _distribution(state, event, policy):
    action = event["action"]
    code, event_id = action["symbol"], action["event_id"]
    if state["phase"] != "open" or state["ordered"] or event_id in state["action_ids"] or code in state["references"]:
        raise ValueError("duplicate or late distribution")
    if action["record_date"] != state["previous"] or action["ex_date"] != state["date"] or not action["evidence_id"] or not action["tax_basis"]:
        raise ValueError("unresolved ownership/action evidence")
    quantity = state["record_quantities"].get(code, 0)
    _equal(event["entitled_quantity"], quantity, "incorrect dividend ownership")
    cash = _cents(quantity * _decimal(action["net_cash_per_share"]))
    shares = quantity * _decimal(action["new_shares_per_share"])
    if quantity <= 0 or cash < 0 or shares < 0 or shares != int(shares):
        raise ValueError("invalid entitlement or fractional shares")
    _equal(event["cash_receivable"], cash, "incorrect dividend receivable")
    _equal(event["shares_receivable"], shares, "incorrect share receivable")
    state["claims"][event_id] = {"action": action, "cash": cash, "shares": int(shares)}
    state["action_ids"].add(event_id)
    state["references"][code] = action["official_reference_price"]


def _release(state, event, policy):
    claim = state["claims"][event["event_id"]]
    if state["phase"] != "open" or state["ordered"] or not claim["shares"] or claim["action"]["shares_listing_date"] > state["date"]:
        raise ValueError("premature or duplicate bonus-share release")
    _equal(event["quantity"], claim["shares"], "bonus quantity mismatch")
    position = state["positions"][claim["action"]["symbol"]]
    position["quantity"] += claim["shares"]
    position["available"] += claim["shares"]
    claim["shares"] = 0


def _payment(state, event, policy):
    claim = state["claims"][event["event_id"]]
    if state["phase"] != "open" or not claim["cash"] or claim["action"]["payment_date"] > state["date"]:
        raise ValueError("premature or duplicate dividend payment")
    _equal(event["amount"], claim["cash"], "cash payment mismatch")
    state["cash"] += claim["cash"]
    claim["cash"], state["closing"] = Decimal(0), True


def _close(state, event, policy):
    if state["phase"] != "open":
        raise ValueError("invalid close transition")
    for claim in state["claims"].values():
        if claim["cash"] and claim["action"]["payment_date"] <= state["date"]:
            raise ValueError("due dividend was not settled at close")
        if claim["shares"] and claim["action"]["shares_listing_date"] <= state["date"]:
            raise ValueError("listed bonus shares were not released")
    market = Decimal(0)
    pending = {code: sum(claim["shares"] for claim in state["claims"].values() if claim["action"]["symbol"] == code) for code in state["positions"]}
    for code, position in state["positions"].items():
        quantity = position["quantity"] + pending[code]
        if quantity:
            _reference(state, code, event["reference_prices"].get(code))
            price = _decimal(event["marks"][code])
            if price <= 0:
                raise ValueError("invalid mark")
            market += quantity * price
            position["last_price"] = float(price)
    receivable = sum((claim["cash"] for claim in state["claims"].values()), Decimal(0))
    snapshot = event["snapshot"]
    for key, value in {"cash": state["cash"], "marketValue": market, "cashReceivable": receivable, "equity": state["cash"] + market + receivable}.items():
        _equal(snapshot[key], value, f"snapshot {key} mismatch")
    if snapshot["positions"] != state["positions"] or snapshot["pendingShares"] != pending:
        raise ValueError("position snapshot mismatch")
    state.update(phase="closed", previous=state["date"], equity=snapshot["equity"], snapshots=state["snapshots"] + 1)
    state["claims"] = {key: claim for key, claim in state["claims"].items() if claim["cash"] or claim["shares"]}


def _reference(state, symbol, preclose):
    if state["record_quantities"].get(symbol):
        expected = state["references"].get(symbol, state["positions"][symbol]["last_price"])
        if preclose is None or abs(_decimal(preclose) - _decimal(expected)) > Decimal("0.01"):
            raise ValueError("unresolved reference price")


def _fees(side, gross, day, policy):
    return {"commission": _cents(max(_decimal(policy["minimum_commission_cny"]), gross * _decimal(policy["commission_rate"]))),
            "stamp_duty": _cents(gross * _rate(policy["stamp_duty"], day)) if side == "SELL" else Decimal(0),
            "transfer_fee": _cents(gross * _rate(policy["transfer_fee"], day))}


def _rate(schedule, day):
    return _decimal([item["rate"] for item in schedule if item["effective"] <= day][-1])


def _decimal(value):
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("nonfinite monetary value")
    return result


def _cents(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _equal(actual, expected, message):
    if abs(_decimal(actual) - _decimal(expected)) > Decimal("0.00000001"):
        raise ValueError(message)
