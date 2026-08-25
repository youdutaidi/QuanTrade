"""State objects owned by the minute paper broker."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Position:
    quantity: int = 0
    available_quantity: int = 0
    average_cost: float = 0.0


@dataclass(frozen=True)
class ExecutionCosts:
    commission: float
    tax: float
    transfer_fee: float

    @property
    def total(self) -> float:
        return self.commission + self.tax + self.transfer_fee

