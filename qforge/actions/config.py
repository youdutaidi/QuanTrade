"""Frozen scope for a resumable annual BaoStock dividend archive."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ActionConfig:
    experiment_id: str
    market_config: str
    database_path: str
    retries: int = 3
    request_timeout_seconds: int = 90
    batch_size: int = 200
    batch_pause_seconds: float = 2.0

    @classmethod
    def from_json(cls, path: str | Path) -> "ActionConfig":
        config = cls(**json.loads(Path(path).read_text(encoding="utf-8")))
        if min(config.retries, config.request_timeout_seconds, config.batch_size) < 1:
            raise ValueError("action retries, timeout and batch size must be positive")
        if config.batch_pause_seconds < 0:
            raise ValueError("action batch pause must not be negative")
        if not config.experiment_id or not config.market_config or not config.database_path:
            raise ValueError("action experiment, market config and database are required")
        return config

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
