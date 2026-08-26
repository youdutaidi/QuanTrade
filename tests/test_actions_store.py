import pandas as pd
import pytest

from qforge.actions.normalization import REQUIRED_FIELDS
from qforge.actions.store import ActionStore


def archive(tmp_path):
    store = ActionStore(tmp_path / "actions.sqlite")
    task = {"code": "sh.600000", "year": 2021}
    store.initialize({"scopeSha256": "fixture", "tasks": [task]})
    return store, task, store.begin_run({"kind": "synthetic"})


def empty_frame():
    frame = pd.DataFrame(columns=sorted(REQUIRED_FIELDS))
    frame.attrs["request"] = {"code": "sh.600000", "year": 2021, "yearType": "operate"}
    return frame


def test_queried_empty_response_is_persisted_and_not_requested_again(tmp_path):
    store, task, run = archive(tmp_path)
    request = store.start_request(task, run)
    assert store.save_response(request, empty_frame()) == 0
    assert store.raw_response(request)["rows"] == []
    assert store.pending_tasks(3, None) == []
    status = store.status()
    assert status["queriedEmptyYears"] == status["requests"] == 1
    assert status["state"] == "source-capture-complete"
    assert status["ledgerReady"] is False
    with pytest.raises(ValueError, match="not active"):
        store.save_response(request, empty_frame())


def test_interrupted_request_retains_history_and_retries_once(tmp_path):
    store, task, run = archive(tmp_path)
    old = store.start_request(task, run)
    assert store.recover() == 1
    assert store.pending_tasks(1, None) == []
    assert store.pending_tasks(3, 1) == [task]
    new = store.start_request(task, store.begin_run({"kind": "resume"}))
    store.save_response(new, empty_frame())
    with store.connect(readonly=True) as conn:
        rows = [tuple(row) for row in conn.execute("SELECT request_id,attempt,status FROM action_requests ORDER BY attempt")]
    assert rows == [(old, 1, "interrupted"), (new, 2, "succeeded")]
    assert store.status()["requests"] == 2


def test_invalid_response_is_not_a_success_and_failed_evidence_survives(tmp_path):
    store, task, run = archive(tmp_path)
    request = store.start_request(task, run)
    frame = empty_frame()
    frame.attrs["request"]["year"] = 2022
    with pytest.raises(ValueError, match="identity"):
        store.save_response(request, frame)
    store.fail_request(request, "wrong year fixture")
    assert store.status()["tasks"] == {"failed": 1}
    assert store.status()["events"] == 0
    assert store.pending_tasks(3, None) == [task]


def test_raw_response_hash_detects_local_tampering(tmp_path):
    store, task, run = archive(tmp_path)
    request = store.start_request(task, run)
    store.save_response(request, empty_frame())
    with store.connect() as conn:
        conn.execute("UPDATE action_requests SET raw_json='{}' WHERE request_id=?", (request,))
    with pytest.raises(ValueError, match="hash changed"):
        store.raw_response(request)


def test_changed_scope_cannot_reuse_checkpoints(tmp_path):
    store, task, _ = archive(tmp_path)
    with pytest.raises(ValueError, match="scope changed"):
        store.initialize({"scopeSha256": "different", "tasks": [task]})
    assert store.status()["tasks"] == {"pending": 1}


def test_nonempty_event_is_atomic_and_cannot_replace_a_completed_response(tmp_path):
    store, task, run = archive(tmp_path)
    request = store.start_request(task, run)
    frame = empty_frame()
    frame.loc[0] = {key: "" for key in frame.columns}
    frame.loc[0, ["code", "dividOperateDate", "dividCashPsBeforeTax"]] = ["sh.600000", "2021-07-01", "0.16000000"]
    assert store.save_response(request, frame) == 1
    assert store.status()["events"] == 1
    assert store.raw_response(request)["rows"][0]["dividCashPsBeforeTax"] == "0.16000000"
    with pytest.raises(ValueError, match="completed action request"):
        store.fail_request(request, "cannot overwrite")
    with store.connect(readonly=True) as conn:
        assert conn.execute("SELECT ledger_ready FROM action_events").fetchone()[0] == 0
