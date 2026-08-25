"""Frozen configuration for one market-data ingestion run."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class MarketDataConfig:
    experiment_id: str
    database_path: str
    start: str
    end: str
    adjustflag: int = 3
    markets: list[str] = field(default_factory=lambda: ["sh", "sz"])
    security_types: list[str] = field(default_factory=lambda: ["1"])
    benchmark_codes: list[str] = field(default_factory=list)
    audit_dates: list[str] = field(default_factory=list)
    retries: int = 3
    request_timeout_seconds: int = 90
    batch_size: int = 200
    batch_pause_seconds: float = 2.0
    source_sample_size: int = 20
    audit_output: str = "research/evidence/QF-DATA-EXPANSION-01/data_audit.json"
    verification_output: str = "research/evidence/QF-DATA-EXPANSION-01/source_sample_replay.json"
    research_panel_output: str = "research/data/qforge_daily_panel.parquet"
    app_output: str | None = None

    @classmethod
    def from_json(cls, path: str | Path) -> "MarketDataConfig":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        config = cls(**payload)
        config.validate()
        return config

    def validate(self) -> None:
        start = date.fromisoformat(self.start)
        end = date.fromisoformat(self.end)
        if start > end:
            raise ValueError("start must not be after end")
        if self.adjustflag not in {1, 2, 3}:
            raise ValueError("adjustflag must be 1, 2, or 3")
        if not self.markets or not set(self.markets) <= {"sh", "sz"}:
            raise ValueError("markets must contain only sh or sz")
        if not self.security_types:
            raise ValueError("security_types must not be empty")
        if any(not code.startswith(("sh.", "sz.")) for code in self.benchmark_codes):
            raise ValueError("benchmark codes must use BaoStock sh./sz. notation")
        if self.retries < 1 or self.request_timeout_seconds < 1 or self.batch_size < 1:
            raise ValueError("retries, request timeout, and batch size must be positive")
        if self.batch_pause_seconds < 0:
            raise ValueError("batch pause must not be negative")
        if self.source_sample_size < 1:
            raise ValueError("source sample size must be positive")
        for value in self.audit_dates:
            audit = date.fromisoformat(value)
            if audit < start or audit > end:
                raise ValueError("audit dates must fall inside the configured window")

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
