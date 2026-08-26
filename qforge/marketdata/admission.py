"""Fail-closed loading contract for a completed, fingerprinted research panel."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq

from .export import file_sha256
from .config import MarketDataConfig


def verify_completed_panel(manifest_path: str | Path, config: MarketDataConfig | None = None) -> dict[str, object]:
    manifest = Path(manifest_path)
    result = json.loads(manifest.read_text(encoding="utf-8"))
    if config is not None:
        keys = ["database_path", "start", "end", "adjustflag", "markets", "security_types", "benchmark_codes"]
        expected = config.as_dict()
        if any(result.get("config", {}).get(key) != expected[key] for key in keys):
            raise ValueError("completed panel configuration does not match the requested data scope")
    if result.get("state") != "ready" or result.get("errors"):
        raise ValueError("data completion manifest is not ready")
    if result.get("audit", {}).get("dataReady") is not True or result.get("verification", {}).get("allPass") is not True:
        raise ValueError("data completion evidence gates did not pass")
    if result["verification"].get("sampleSize", 0) < 1:
        raise ValueError("data completion evidence has no source replay sample")
    panel = result.get("panel")
    if not isinstance(panel, dict) or not panel.get("output") or not panel.get("sha256"):
        raise ValueError("data completion manifest has no fingerprinted panel")
    path = Path(panel["output"])
    if not path.is_file() or file_sha256(path) != panel["sha256"]:
        raise ValueError("research panel file is missing or its fingerprint changed")
    metadata = pq.read_metadata(path)
    if metadata.num_rows <= 0 or metadata.num_rows != panel["rows"]:
        raise ValueError("research panel row count does not match completion evidence")
    return {
        "state": "verified-input", "manifest": str(manifest), "panel": str(path),
        "rows": metadata.num_rows, "sha256": panel["sha256"],
        "scope": "research input only; corporate-action P&L and strategy validation remain separate",
    }
