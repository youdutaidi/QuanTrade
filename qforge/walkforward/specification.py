"""Immutable textual study specification and deterministic candidate expansion."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


@dataclass(frozen=True)
class Candidate:
    family: str
    rebalance_days: int
    top_n: int
    lookback: int = 0
    skip: int = 0
    window: str = ""

    @property
    def candidate_id(self) -> str:
        setting = self.window or f"{self.lookback}d-skip{self.skip}"
        return f"{self.family}__{setting}__r{self.rebalance_days}__n{self.top_n}"


@dataclass(frozen=True)
class StudySpec:
    source_json: str

    @classmethod
    def from_json(cls, path: str | Path) -> "StudySpec":
        spec = cls(Path(path).read_text(encoding="utf-8"))
        spec.validate()
        return spec

    @property
    def values(self) -> dict:
        # A new copy prevents a caller from mutating the frozen definition.
        return json.loads(self.source_json)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.source_json.encode("utf-8")).hexdigest()

    def candidates(self) -> tuple[Candidate, ...]:
        values = self.values
        candidates = []
        for family, grid in values["grid"].items():
            keys = sorted(grid)
            choices = itertools.product(*(grid[key] for key in keys))
            for choice in choices:
                for rebalance, top_n in itertools.product(values["rebalance_days"], values["top_n"]):
                    candidates.append(Candidate(family, rebalance, top_n, **dict(zip(keys, choice))))
        return tuple(sorted(candidates, key=lambda item: item.candidate_id))

    def validate(self) -> None:
        values = self.values
        if values["version"] != 1:
            raise ValueError("unsupported study version")
        _validate_grid(values, self.candidates())
        _validate_periods(values["periods"])
        _validate_signal_policy(values)
        _validate_execution(values["execution"])
        if values["selection"]["holdout_openings"] != 1:
            raise ValueError("the final holdout may be opened only once")


def _validate_grid(values: dict, candidates: tuple[Candidate, ...]) -> None:
    expected = {"residual_momentum", "short_reversal", "low_idiosyncratic_volatility",
                "low_maximum_return", "fixed_equal_composite"}
    if set(values["grid"]) != expected:
        raise ValueError("unexpected candidate family")
    if len(candidates) != values["expected_candidates"] or len({c.candidate_id for c in candidates}) != len(candidates):
        raise ValueError("candidate count or uniqueness mismatch")
    for item in candidates:
        if item.rebalance_days < 1 or item.top_n < 1 or 1 / item.top_n > values["execution"]["max_stock_weight"]:
            raise ValueError("invalid rebalance frequency or concentration")
        if item.family == "fixed_equal_composite":
            if item.window not in values["signals"]["composite_windows"]:
                raise ValueError("unknown composite window")
        elif item.lookback < 2 or item.skip < 0:
            raise ValueError("invalid signal window")


def _validate_periods(periods: dict) -> None:
    windows = [periods["discovery"], *(fold["test"] for fold in periods["folds"]), periods["holdout"]]
    dates = [(date.fromisoformat(start), date.fromisoformat(end)) for start, end in windows]
    if len(periods["folds"]) < 3 or any(start >= end for start, end in dates):
        raise ValueError("invalid study windows")
    if any(dates[i][0] != dates[i - 1][1] + timedelta(days=1) for i in range(1, len(dates))):
        raise ValueError("study windows must be disjoint and contiguous")
    for fold in periods["folds"]:
        if date.fromisoformat(fold["train_end"]) >= date.fromisoformat(fold["test"][0]):
            raise ValueError("training must end before fold evaluation")


def _validate_signal_policy(values: dict) -> None:
    signals, universe = values["signals"], values["universe"]
    if signals["beta_lag"] != 1 or signals["beta_lookback"] < 2 or signals["std_ddof"] != 1:
        raise ValueError("residuals require lagged sample OLS")
    if not signals["remove_intercept"] or signals["mad_clip"] <= 0:
        raise ValueError("unsupported residual or standardization policy")
    if universe["liquidity_lag"] < 1 or universe["liquidity_lookback"] < 2:
        raise ValueError("liquidity must be lagged")
    if universe["minimum_listing_sessions"] < 120 or not universe["exclude_st"]:
        raise ValueError("study excludes recent IPOs and ST buys")
    if universe["minimum_median_amount_cny"] <= 0:
        raise ValueError("liquidity floor must be positive")
    definitions = {
        "residual_momentum": "rolling_sum_divided_by_sample_standard_deviation",
        "short_reversal": "negative_compounded_return",
        "low_idiosyncratic_volatility": "negative_sample_standard_deviation",
        "low_maximum_return": "negative_maximum_single_day_return",
    }
    if any(signals[key] != definition for key, definition in definitions.items()):
        raise ValueError("unsupported signal definition")


def _validate_execution(policy: dict) -> None:
    start, end = (date.fromisoformat(value) for value in policy["supported_dates"])
    if start >= end or policy["initial_cash_cny"] <= 0:
        raise ValueError("invalid execution scope or capital")
    if not policy["long_only"] or policy["leverage"] != 1 or not policy["t_plus_one"]:
        raise ValueError("study permits only unlevered long-only T+1 portfolios")
    if policy["volume_lag"] < 1 or not 0 < policy["share_volume_participation"] <= 0.01:
        raise ValueError("capacity must use conservative lagged volume")
    for key in ["commission_rate", "minimum_commission_cny", "slippage_bps"]:
        if not math.isfinite(policy[key]) or policy[key] < 0:
            raise ValueError("execution costs cannot be negative")
    for key in ["stamp_duty", "transfer_fee", "mainboard_st_limit"]:
        dates = [date.fromisoformat(item["effective"]) for item in policy[key]]
        if not dates or dates[0] > start or dates != sorted(set(dates)) or dates[-1] > end:
            raise ValueError(f"invalid {key} effective-date schedule")
        if any(not 0 <= item["rate"] < 1 for item in policy[key]):
            raise ValueError(f"invalid {key} rate")
