from __future__ import annotations

from qforge.marketdata.complete import _write_json


def test_completion_evidence_writer_creates_parent(tmp_path) -> None:
    output = tmp_path / "evidence" / "audit.json"
    _write_json(output, {"dataReady": False})
    assert output.read_text(encoding="utf-8") == '{\n  "dataReady": false\n}'
