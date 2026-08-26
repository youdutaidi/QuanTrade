"""Finish all recoverable data work and admit only a fully audited database."""

from __future__ import annotations

import json
from pathlib import Path

from .audit import audit_market_database
from .config import MarketDataConfig
from .panel import export_research_panel
from .service import download_daily, market_status
from .verify import verify_source_sample


def complete_market_data(config: MarketDataConfig, root: Path) -> dict[str, object]:
    passes: list[dict[str, object]] = []
    for pass_index in range(1, config.retries + 1):
        try:
            result = download_daily(config, root, recover=True)
        except Exception as error:
            passes.append({"pass": pass_index, "state": "failed", "error": repr(error)})
            continue
        passes.append({
            "pass": pass_index,
            "selectedTasks": result["selectedTasks"],
            "rowsWritten": result["rowsWritten"],
            "failures": result["failures"],
        })
        if result["failures"] == 0:
            break
    audit = audit_market_database(config, root)
    _write_json(root / config.audit_output, audit)
    verification: dict[str, object] = {"sampleSize": 0, "allPass": False, "state": "skipped-until-data-ready"}
    panel: dict[str, object] | None = None
    if audit["dataReady"]:
        try:
            verification = verify_source_sample(config, root, config.source_sample_size)
        except Exception as error:
            verification = {"sampleSize": 0, "allPass": False, "state": "failed", "error": repr(error)}
        _write_json(root / config.verification_output, verification)
        if verification["allPass"]:
            panel = export_research_panel(
                root / config.database_path,
                root / config.research_panel_output,
                config.start,
                config.end,
                config.adjustflag,
            )
    inventory = market_status(config, root)
    ready = bool(audit["dataReady"] and verification["allPass"] and panel)
    return {
        "state": "ready" if ready else "incomplete",
        "passes": passes,
        "audit": {key: audit[key] for key in ["quickCheck", "tasksComplete", "integrityPass", "dataReady"]},
        "verification": {"sampleSize": verification["sampleSize"], "allPass": verification["allPass"]},
        "panel": panel,
        "inventory": inventory,
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
