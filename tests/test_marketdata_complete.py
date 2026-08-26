from __future__ import annotations

from qforge.marketdata.complete import _write_json


def test_completion_evidence_writer_creates_parent(tmp_path) -> None:
    output = tmp_path / "evidence" / "audit.json"
    _write_json(output, {"dataReady": False})
    assert output.read_text(encoding="utf-8") == '{\n  "dataReady": false\n}'


def test_completion_recovers_after_download_exception(tmp_path, monkeypatch) -> None:
    import qforge.marketdata.complete as module
    from qforge.marketdata.config import MarketDataConfig

    calls = []

    def download(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("transient login failure")
        return {"selectedTasks": 0, "rowsWritten": 0, "failures": 0}

    monkeypatch.setattr(module, "download_daily", download)
    monkeypatch.setattr(module, "audit_market_database", lambda *args: {
        "quickCheck": "ok", "tasksComplete": False, "integrityPass": True, "dataReady": False,
    })
    monkeypatch.setattr(module, "market_status", lambda *args: {})
    config = MarketDataConfig("test", "market.sqlite", "2020-01-01", "2020-12-31")
    result = module.complete_market_data(config, tmp_path)
    assert len(calls) == 2
    assert result["state"] == "incomplete"
    assert result["passes"][0]["state"] == "failed"
