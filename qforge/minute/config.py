"""Configuration contract for one minute-data paper experiment."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class MinuteConfig:
    experiment_id: str
    database_path: str
    frequency: int
    adjustflag: int
    start: str
    end: str
    symbols: list[str]
    strategy: str = "close_strength"
    design_end: str | None = None
    signal_time: str = "14:50:00"
    top_n: int = 3
    initial_cash: float = 1_000_000.0
    lot_size: int = 100
    commission_rate: float = 0.0003
    minimum_commission: float = 5.0
    stamp_duty_rate: float = 0.0005
    transfer_fee_rate: float = 0.00001
    slippage_bps: float = 5.0
    max_participation: float = 0.05
    limit_pct: float = 0.10
    output_dir: str = "research/output/minute_engine"
    app_output: str | None = None

    @classmethod
    def from_json(cls, path: str | Path) -> "MinuteConfig":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        config = cls(**payload)
        config.validate()
        return config

    def validate(self) -> None:
        if self.frequency not in {5, 15, 30, 60}:
            raise ValueError("frequency must be one of 5, 15, 30, 60")
        if self.adjustflag not in {1, 2, 3}:
            raise ValueError("adjustflag must be 1, 2, or 3")
        if not self.symbols or len(set(self.symbols)) != len(self.symbols):
            raise ValueError("symbols must be non-empty and unique")
        if not 0 < self.top_n <= len(self.symbols):
            raise ValueError("top_n must fit inside the symbol universe")
        if self.lot_size < 1 or not 0 < self.max_participation <= 1:
            raise ValueError("invalid lot size or max participation")
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be positive")

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

