"""Pure pre-opening target quantities; actual open/close are never inputs."""

from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR
from dataclasses import dataclass

import pandas as pd

from .models import OrderIntent
from .signals import equal_weight_targets
from .specification import Candidate


@dataclass(frozen=True)
class RebalancePlan:
    orders: tuple[OrderIntent, ...]
    target_weights: dict[str, float]
    desired_shares: dict[str, int]


def plan_rebalance(candidate: Candidate, scores: pd.Series, equity: float, economic_shares: dict[str, int],
                   references: dict[str, float], signal_date: str, execution_date: str, max_weight: float) -> RebalancePlan:
    budget = Decimal(str(equity))
    if not budget.is_finite() or budget <= 0:
        raise ValueError("order sizing needs positive prior-close equity")
    targets = equal_weight_targets(scores, candidate.top_n, max_weight)
    symbols = sorted(set(targets.index) | {code for code, quantity in economic_shares.items() if quantity})
    desired, sell, buy = {}, [], {}
    for code in symbols:
        held = economic_shares.get(code, 0)
        if isinstance(held, bool) or not isinstance(held, int) or held < 0:
            raise ValueError("economic share balance must be a nonnegative integer")
        if references.get(code) is None:
            raise ValueError("pre-opening reference price is missing or invalid")
        price = Decimal(str(references[code]))
        if not price.is_finite() or price <= 0:
            raise ValueError("pre-opening reference price is missing or invalid")
        weight = Decimal(str(targets.get(code, 0)))
        desired[code] = int((budget * weight / price).to_integral_value(rounding=ROUND_FLOOR))
        difference = desired[code] - held
        if not difference:
            continue
        side = "BUY" if difference > 0 else "SELL"
        order = OrderIntent(f"{candidate.candidate_id}:{execution_date}:{code}", code, side,
                            abs(difference), signal_date, execution_date)
        if side == "SELL":
            sell.append(order)
        else:
            buy[code] = order
    orders = sell + [buy[code] for code in targets.index if code in buy]
    return RebalancePlan(tuple(orders), targets.to_dict(), desired)
