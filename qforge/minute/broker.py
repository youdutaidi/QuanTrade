"""A-share paper broker: next-bar fills, T+1 inventory, board lots and costs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pandas as pd

from .config import MinuteConfig
from .models import ExecutionCosts, Position
from .store import MinuteStore, now_iso


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str
    quantity: int


class PaperBroker:
    def __init__(self, config: MinuteConfig, store: MinuteStore, run_id: str):
        self.config = config
        self.store = store
        self.run_id = run_id
        self.cash = config.initial_cash
        self.positions: dict[str, Position] = {}
        self.current_date: object | None = None
        self.peak_equity = config.initial_cash

    def advance_date(self, trade_date: object) -> None:
        if self.current_date == trade_date:
            return
        for position in self.positions.values():
            position.available_quantity = position.quantity
        self.current_date = trade_date

    def rebalance(
        self,
        targets: pd.Series,
        execution_bars: pd.DataFrame,
        previous_closes: dict[str, float],
    ) -> None:
        prices = execution_bars.set_index("symbol")["open"].to_dict()
        equity = self.cash + sum(position.quantity * prices.get(symbol, 0) for symbol, position in self.positions.items())
        target_qty = self._target_quantities(targets, prices, equity)
        intents = self._order_intents(target_qty)
        bar_map = {row.symbol: row._asdict() for row in execution_bars.itertuples(index=False)}
        for intent in sorted(intents, key=lambda item: item.side != "SELL"):
            self._execute(intent, bar_map.get(intent.symbol), previous_closes.get(intent.symbol))

    def _target_quantities(self, targets: pd.Series, prices: dict[str, float], equity: float) -> dict[str, int]:
        result = {}
        for symbol in set(self.positions) | set(targets.index):
            price = prices.get(symbol)
            weight = float(targets.get(symbol, 0))
            lots = int((equity * weight / price) // self.config.lot_size) if price and price > 0 else 0
            result[symbol] = lots * self.config.lot_size
        return result

    def _order_intents(self, targets: dict[str, int]) -> list[OrderIntent]:
        intents = []
        for symbol, target in targets.items():
            current = self.positions.get(symbol, Position()).quantity
            difference = target - current
            if difference > 0:
                intents.append(OrderIntent(symbol, "BUY", difference))
            elif difference < 0:
                intents.append(OrderIntent(symbol, "SELL", -difference))
        return intents

    def _execute(self, intent: OrderIntent, bar: dict[str, object] | None, previous_close: float | None) -> None:
        order_id = f"order-{uuid.uuid4().hex}"
        quantity, reason = self._fillable_quantity(intent, bar, previous_close)
        if quantity <= 0:
            self._record_order(order_id, intent, 0, "rejected", reason, bar)
            return
        raw_price = float(bar["open"])
        price = raw_price * (1 + self.config.slippage_bps / 10_000 * (1 if intent.side == "BUY" else -1))
        quantity = self._affordable_quantity(intent, quantity, price)
        if quantity <= 0:
            self._record_order(order_id, intent, 0, "rejected", "insufficient_cash", bar)
            return
        costs = self._costs(intent.side, quantity * price)
        self._apply_fill(intent, quantity, price, costs)
        status = "filled" if quantity == intent.quantity else "partial"
        self._record_order(order_id, intent, quantity, status, reason, bar)
        self._record_fill(order_id, intent, quantity, price, costs, bar)

    def _fillable_quantity(
        self,
        intent: OrderIntent,
        bar: dict[str, object] | None,
        previous_close: float | None,
    ) -> tuple[int, str | None]:
        if not bar or float(bar["volume"]) <= 0:
            return 0, "no_tradable_bar"
        if self._is_locked(intent.side, bar, previous_close):
            return 0, "locked_limit"
        available = self.positions.get(intent.symbol, Position()).available_quantity
        requested = min(intent.quantity, available) if intent.side == "SELL" else intent.quantity
        if requested <= 0:
            return 0, "t_plus_one"
        capacity = int(float(bar["volume"]) * self.config.max_participation // self.config.lot_size) * self.config.lot_size
        quantity = min(requested, capacity)
        return quantity, "participation_cap" if quantity < intent.quantity else None

    def _is_locked(self, side: str, bar: dict[str, object], previous_close: float | None) -> bool:
        if not previous_close or float(bar["high"]) != float(bar["low"]):
            return False
        change = float(bar["open"]) / previous_close - 1
        return (side == "BUY" and change >= self.config.limit_pct - 1e-6) or (side == "SELL" and change <= -self.config.limit_pct + 1e-6)

    def _affordable_quantity(self, intent: OrderIntent, quantity: int, price: float) -> int:
        if intent.side == "SELL":
            return quantity
        lot = self.config.lot_size
        while quantity > 0:
            costs = self._costs("BUY", quantity * price)
            if quantity * price + costs.total <= self.cash:
                return quantity
            quantity -= lot
        return 0

    def _costs(self, side: str, gross: float) -> ExecutionCosts:
        commission = max(self.config.minimum_commission, gross * self.config.commission_rate)
        tax = gross * self.config.stamp_duty_rate if side == "SELL" else 0.0
        transfer = gross * self.config.transfer_fee_rate
        return ExecutionCosts(commission, tax, transfer)

    def _apply_fill(self, intent: OrderIntent, quantity: int, price: float, costs: ExecutionCosts) -> None:
        position = self.positions.setdefault(intent.symbol, Position())
        gross = quantity * price
        if intent.side == "BUY":
            total_cost = position.average_cost * position.quantity + gross
            position.quantity += quantity
            position.average_cost = total_cost / position.quantity
            self.cash -= gross + costs.total
            return
        position.quantity -= quantity
        position.available_quantity -= quantity
        self.cash += gross - costs.total
        if position.quantity == 0:
            position.average_cost = 0.0

    def _record_order(self, order_id: str, intent: OrderIntent, filled: int, status: str, reason: str | None, bar: dict[str, object] | None) -> None:
        self.store.write_order({
            "order_id": order_id, "run_id": self.run_id, "bar_time": str(bar["bar_time"]) if bar else now_iso(),
            "symbol": intent.symbol, "side": intent.side, "requested_qty": intent.quantity, "filled_qty": filled,
            "status": status, "reason": reason, "created_at": now_iso(),
        })

    def _record_fill(self, order_id: str, intent: OrderIntent, quantity: int, price: float, costs: ExecutionCosts, bar: dict[str, object]) -> None:
        self.store.write_fill({
            "fill_id": f"fill-{uuid.uuid4().hex}", "order_id": order_id, "run_id": self.run_id,
            "bar_time": str(bar["bar_time"]), "symbol": intent.symbol, "side": intent.side,
            "quantity": quantity, "price": price, "gross_value": quantity * price,
            "commission": costs.commission, "tax": costs.tax, "transfer_fee": costs.transfer_fee,
        })

    def position_records(self, run_id: str, bar_time: pd.Timestamp, prices: dict[str, float]) -> list[tuple[object, ...]]:
        return [
            (run_id, str(bar_time), symbol, position.quantity, position.available_quantity, position.average_cost, prices.get(symbol, 0.0))
            for symbol, position in self.positions.items() if position.quantity > 0
        ]

    def equity_record(self, run_id: str, bar_time: pd.Timestamp, prices: dict[str, float]) -> tuple[object, ...]:
        market_value = sum(position.quantity * prices.get(symbol, 0.0) for symbol, position in self.positions.items())
        equity = self.cash + market_value
        self.peak_equity = max(self.peak_equity, equity)
        drawdown = equity / self.peak_equity - 1
        return run_id, str(bar_time), self.cash, market_value, equity, drawdown
