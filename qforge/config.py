"""Configuration contract for one reproducible factor experiment."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class BacktestConfig:
    experiment_id: str
    data_path: str
    start: str
    end: str
    factors: list[str]
    membership_path: str | None = None
    benchmark_symbol: str | None = None
    design_end: str | None = None
    include_composite: bool = True
    rebalance_days: int = 5
    top_quantile: float = 0.1
    quantiles: int = 5
    liquidity_floor_pct: float = 0.3
    winsor_mad: float = 5.0
    buy_cost_bps: float = 15.0
    sell_cost_bps: float = 20.0
    market_regime_days: int = 0
    simulate_locked_limits: bool = True
    limit_pct: float = 0.095
    output_dir: str = "research/output/factor_engine"
    app_output: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_json(cls, path: str | Path) -> "BacktestConfig":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        config = cls(**payload)
        config.validate()
        return config

    def validate(self) -> None:
        if not self.experiment_id.strip():
            raise ValueError("experiment_id must be non-empty")
        if not self.factors:
            raise ValueError("at least one factor is required")
        if not 0 < self.top_quantile <= 0.5:
            raise ValueError("top_quantile must be in (0, 0.5]")
        if not 0 <= self.liquidity_floor_pct < 1:
            raise ValueError("liquidity_floor_pct must be in [0, 1)")
        if self.rebalance_days < 1 or self.quantiles < 2:
            raise ValueError("rebalance_days >= 1 and quantiles >= 2 are required")

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
