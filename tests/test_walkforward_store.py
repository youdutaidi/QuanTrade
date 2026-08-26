from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from qforge.walkforward.demo import run_ledger_demo
from qforge.walkforward.ledger_audit import audit_ledger
from qforge.walkforward.specification import StudySpec
from qforge.walkforward.store import load_ledger


def test_sqlite_persistence_round_trip_and_tamper_detection(tmp_path):
    spec = StudySpec.from_json(Path(__file__).resolve().parents[1] / "configs/walk_forward.json")
    first = run_ledger_demo(spec, tmp_path, tmp_path / "first")
    second = run_ledger_demo(spec, tmp_path, tmp_path / "second")
    assert first["runId"] != second["runId"]
    assert first["eventsSha256"] == second["eventsSha256"]
    assert first["notMarketBacktest"] and not first["verifiedStrategy"]
    events, metadata = load_ledger(Path(first["database"]), first["runId"])
    assert audit_ledger(events, spec.values["execution"])["allPass"]
    assert metadata["kind"] == "synthetic" and metadata["verified_strategy"] == 0
    with pytest.raises(FileExistsError):
        run_ledger_demo(spec, tmp_path, tmp_path / "first")
    with sqlite3.connect(first["database"]) as connection:
        connection.execute("UPDATE study_ledger_events SET event_json=? WHERE run_id=? AND sequence=0", (json.dumps({}), first["runId"]))
    with pytest.raises(ValueError, match="fingerprint"):
        load_ledger(Path(first["database"]), first["runId"])
    assert load_ledger(Path(second["database"]), second["runId"])[0] == events
