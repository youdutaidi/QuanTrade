"""Workflow composing source ingestion, audit witnesses, replay and export."""

from __future__ import annotations

from pathlib import Path

from .audit import audit_market_database
from .config import MarketDataConfig
from .completion_evidence import begin_completion_evidence, finish_completion_evidence, market_code_sha256, write_json
from .panel import export_research_panel
from .service import download_daily, market_status
from .verify import verify_source_sample


def complete_market_data(config: MarketDataConfig, root: Path) -> dict[str, object]:
    directory, metadata = begin_completion_evidence(config, root)
    passes = _download_passes(config, root)
    audit = audit_market_database(config, root)
    _write_json(root / config.audit_output, audit)
    _write_json(directory / "audit.json", audit)
    verification, panel, errors = _verify_and_export(config, root, bool(audit["dataReady"]))
    if panel and panel["rows"] != audit["coverage"]["expectedRows"]:
        errors.append("exported panel row count does not match audited calendar coverage")
    _write_json(directory / "source_replay.json", verification)
    _write_json(directory / "panel.json", {"panel": panel, "errors": errors})
    if metadata["codeSha256"] != market_code_sha256():
        errors.append("market-data code changed during completion; rerun under a frozen code identity")
    inventory = market_status(config, root)
    ready = bool(audit["dataReady"] and verification["allPass"] and panel and not errors)
    result = {
        **metadata, "state": "ready" if ready else "incomplete", "passes": passes, "errors": errors,
        "audit": {key: audit[key] for key in ["quickCheck", "tasksComplete", "integrityPass", "dataReady"]},
        "verification": {"sampleSize": verification["sampleSize"], "allPass": verification["allPass"]},
        "panel": panel, "inventory": inventory,
        "scope": "raw and adjusted-price research input; not verified strategy or corporate-action P&L",
    }
    return finish_completion_evidence(config, root, directory, result)


def _download_passes(config: MarketDataConfig, root: Path) -> list[dict[str, object]]:
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
    return passes


def _verify_and_export(config: MarketDataConfig, root: Path, data_ready: bool) -> tuple[dict, dict | None, list[str]]:
    verification: dict[str, object] = {"sampleSize": 0, "allPass": False, "state": "skipped-until-data-ready"}
    panel: dict[str, object] | None = None
    errors = []
    if data_ready:
        try:
            verification = verify_source_sample(config, root, config.source_sample_size)
        except Exception as error:
            verification = {"sampleSize": 0, "allPass": False, "state": "failed", "error": repr(error)}
        _write_json(root / config.verification_output, verification)
        if verification["allPass"]:
            try:
                panel = export_research_panel(root / config.database_path, root / config.research_panel_output, config.start, config.end, config.adjustflag)
            except Exception as error:
                errors.append(f"panel export failed: {error!r}")
    return verification, panel, errors


def _write_json(path: Path, payload: dict[str, object]) -> None:
    write_json(path, payload)
