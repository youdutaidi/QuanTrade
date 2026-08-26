"""Pure, bounded order sizing and fill decisions for the paper ledger."""

from __future__ import annotations

from decimal import Decimal
from datetime import date

from .models import FillDecision, OpeningQuote, OrderIntent
from .rules import board_for_symbol, execution_costs, normalize_quantity, opening_fill_price, price_limits


def decide_fill(order: OrderIntent, quote: OpeningQuote, cash: Decimal, available: int, policy: dict) -> FillDecision:
    for value in [order.signal_date, order.execution_date, quote.trade_date, quote.capacity_asof]:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError("order and quote dates must use YYYY-MM-DD")
    if order.side not in {"BUY", "SELL"} or not isinstance(quote.tradeable, bool) or not isinstance(quote.is_st, bool):
        raise ValueError("invalid order side or unknown trading/ST status")
    if order.symbol != quote.symbol or order.execution_date != quote.trade_date:
        raise ValueError("order and opening quote identities disagree")
    if quote.capacity_asof > order.signal_date or order.signal_date >= order.execution_date:
        raise ValueError("capacity or signal is not available before execution")
    if not quote.tradeable or order.side == "BUY" and quote.is_st:
        return _reject("not_tradeable_or_st_buy")
    lower, upper = price_limits(order.symbol, quote.preclose, quote.trade_date, quote.is_st, policy)
    price = opening_fill_price(order.side, quote.raw_open, lower, upper, policy["slippage_bps"])
    if price is None:
        return _reject("opening_limit_or_unresolved_session")
    quantity = normalize_quantity(order.symbol, order.side, order.quantity, available, quote.capacity, policy)
    if order.side == "BUY":
        quantity = affordable_quantity(order.symbol, quantity, price, cash, quote.trade_date, policy)
    if quantity == 0:
        return _reject("lot_capacity_inventory_or_cash")
    costs = execution_costs(order.side, float(Decimal(quantity) * Decimal(str(price))), quote.trade_date, policy)
    return FillDecision(quantity, price, costs.commission, costs.stamp_duty, costs.transfer_fee,
                        "filled" if quantity == order.quantity else "partial_cancel_remainder")


def affordable_quantity(symbol: str, maximum: int, price: float, cash: Decimal, trade_date: str, policy: dict) -> int:
    rule = policy["board_rules"][board_for_symbol(symbol)]
    minimum, step = rule["minimum"], rule["step"]
    if maximum < minimum:
        return 0
    low, high = -1, (maximum - minimum) // step
    while low < high:
        middle = (low + high + 1) // 2
        quantity = minimum + middle * step
        gross = Decimal(quantity) * Decimal(str(price))
        costs = execution_costs("BUY", float(gross), trade_date, policy)
        fees = sum(Decimal(str(value)) for value in [costs.commission, costs.stamp_duty, costs.transfer_fee])
        if gross + fees <= cash:
            low = middle
        else:
            high = middle - 1
    return 0 if low < 0 else minimum + low * step


def _reject(reason: str) -> FillDecision:
    return FillDecision(0, 0.0, 0.0, 0.0, 0.0, reason)
