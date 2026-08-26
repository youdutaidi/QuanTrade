"""Append-only completion evidence and an atomic latest-result pointer."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from .config import MarketDataConfig


def begin_completion_evidence(config: MarketDataConfig, root: Path) -> tuple[Path, dict[str, object]]:
    run_id = f"completion-{uuid.uuid4().hex}"
    directory = (root / config.audit_output).parent / "completion_runs" / run_id
    directory.mkdir(parents=True, exist_ok=False)
    metadata = {
        "runId": run_id, "startedAt": datetime.now(UTC).isoformat(),
        "config": config.as_dict(), "codeSha256": market_code_sha256(),
    }
    write_json(directory / "started.json", metadata)
    return directory, metadata


def finish_completion_evidence(
    config: MarketDataConfig, root: Path, directory: Path, payload: dict[str, object],
) -> dict[str, object]:
    result = {**payload, "completedAt": datetime.now(UTC).isoformat(), "manifest": str(directory / "result.json")}
    write_json(directory / "result.json", result)
    write_json((root / config.audit_output).parent / "data_completion.json", result)
    return result


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=f".{path.name}-", dir=path.parent) as directory:
        staged = Path(directory) / "result.json"
        staged.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        staged.replace(path)


def market_code_sha256() -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()
