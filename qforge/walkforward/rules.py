"""Date-aware, conservative A-share order primitives, independent of OHLC outcomes.

Only mature ordinary A-shares in the frozen study window are supported. IPO,
relisting and other exceptional no-limit sessions require separate evidence.
These primitives are not an opening-auction liquidity or broker execution proof.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


@dataclass(frozen=True)
class TradeCosts:
    commission: float
    stamp_duty: float
    transfer_fee: float

    @property
    def total(self) -> float:
        return self.commission + self.stamp_duty + self.transfer_fee


def board_for_symbol(symbol: str) -> str:
    if re.fullmatch(r"sh\.68\d{4}", symbol):
        return "star"
    if re.fullmatch(r"sz\.30\d{4}", symbol):
        return "chinext"
    if re.fullmatch(r"(?:sh\.60|sz\.00)\d{4}", symbol):
        return "main"
    raise ValueError(f"unsupported ordinary A-share symbol: {symbol}")


def effective_rate(schedule: list[dict], trade_date: str, policy: dict) -> float:
    _check_date(trade_date, policy)
    parsed = date.fromisoformat(trade_date)
    rates = [row["rate"] for row in schedule if date.fromisoformat(row["effective"]) <= parsed]
    if not rates:
        raise ValueError("no rule for execution date")
    return float(rates[-1])


def execution_costs(side: str, gross: float, trade_date: str, policy: dict) -> TradeCosts:
    _check_side(side)
    _check_date(trade_date, policy)
    if not math.isfinite(gross) or gross < 0:
        raise ValueError("gross value must be nonnegative and finite")
    if gross == 0:
        return TradeCosts(0.0, 0.0, 0.0)
    amount = Decimal(str(gross))
    commission = max(Decimal(str(policy["minimum_commission_cny"])), amount * Decimal(str(policy["commission_rate"])))
    stamp = amount * Decimal(str(effective_rate(policy["stamp_duty"], trade_date, policy))) if side == "SELL" else Decimal(0)
    transfer = amount * Decimal(str(effective_rate(policy["transfer_fee"], trade_date, policy)))
    return TradeCosts(*(_money(value) for value in [commission, stamp, transfer]))


def price_limits(symbol: str, preclose: float, trade_date: str, is_st: bool, policy: dict) -> tuple[float, float]:
    _check_date(trade_date, policy)
    board = board_for_symbol(symbol)
    if not math.isfinite(preclose) or preclose <= 0:
        raise ValueError("exchange reference price must be positive and finite")
    rate = policy["board_rules"][board]["price_limit"]
    if board == "main" and is_st:
        rate = effective_rate(policy["mainboard_st_limit"], trade_date, policy)
    reference, fraction = Decimal(str(preclose)), Decimal(str(rate))
    return _money(reference * (1 - fraction)), _money(reference * (1 + fraction))


def opening_fill_price(side: str, raw_open: float, lower: float, upper: float, slippage_bps: float) -> float | None:
    _check_side(side)
    values = [raw_open, lower, upper, slippage_bps]
    if not all(math.isfinite(value) for value in values) or lower <= 0 or upper < lower or slippage_bps < 0:
        raise ValueError("invalid price bounds or slippage")
    if raw_open < lower or raw_open > upper:
        return None  # Exceptional/no-limit session: do not invent ordinary fills.
    if (side == "BUY" and raw_open >= upper) or (side == "SELL" and raw_open <= lower):
        return None
    sign = 1 if side == "BUY" else -1
    modeled = Decimal(str(raw_open)) * (1 + sign * Decimal(str(slippage_bps)) / 10000)
    rounding = ROUND_CEILING if side == "BUY" else ROUND_FLOOR
    price = float(modeled.quantize(Decimal("0.01"), rounding=rounding))
    return price if lower <= price <= upper else None


def normalize_quantity(symbol: str, side: str, requested: int, available: int, capacity: int, policy: dict) -> int:
    """Conservative subset of valid lot orders; SELL available excludes T+0 buys."""
    _check_side(side)
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in [requested, available, capacity]):
        raise ValueError("share quantities must be nonnegative integers")
    rule = policy["board_rules"][board_for_symbol(symbol)]
    quantity = min(requested, capacity, rule["max_limit_order"])
    if side == "SELL":
        quantity = min(quantity, available)
        if quantity == available:
            return quantity  # Includes sale of the entire available odd-lot balance.
    if quantity < rule["minimum"]:
        return 0
    return rule["minimum"] + ((quantity - rule["minimum"]) // rule["step"]) * rule["step"]


def _check_date(trade_date: str, policy: dict) -> None:
    parsed = date.fromisoformat(trade_date)
    start, end = (date.fromisoformat(value) for value in policy["supported_dates"])
    if parsed < start or parsed > end:
        raise ValueError("execution date outside the verified rule window")


def _check_side(side: str) -> None:
    if side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")


def _money(value: float | Decimal) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
