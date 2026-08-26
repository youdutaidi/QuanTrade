"""Explicit inputs for the paper ledger; no source or broker side effects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OrderIntent:
    order_id: str
    symbol: str
    side: str
    quantity: int
    signal_date: str
    execution_date: str


@dataclass(frozen=True)
class OpeningQuote:
    symbol: str
    trade_date: str
    raw_open: float | None
    preclose: float
    is_st: bool
    tradeable: bool
    capacity: int
    capacity_asof: str


@dataclass(frozen=True)
class Distribution:
    """Net cash/tax and share allocation must come from explicit event evidence.

    The ledger does not infer these from adjustment factors, nor claim that a
    provider's generic 'after tax' field matches an investor's holding period.
    """
    event_id: str
    symbol: str
    record_date: str
    ex_date: str
    net_cash_per_share: float
    new_shares_per_share: float
    payment_date: str | None
    shares_listing_date: str | None
    official_reference_price: float
    evidence_id: str
    tax_basis: str


@dataclass
class Position:
    quantity: int = 0
    available: int = 0
    last_price: float | None = None


@dataclass(frozen=True)
class FillDecision:
    quantity: int
    price: float
    commission: float
    stamp_duty: float
    transfer_fee: float
    reason: str
