import argparse
import json

import pandas as pd
import pytest

import qforge.actions.audit as audit_module
from qforge.actions.audit import audit_action_archive
from qforge.actions.cli import run_action_command
from qforge.actions.config import ActionConfig
from qforge.actions.normalization import REQUIRED_FIELDS
from qforge.actions.store import ActionStore


def fixture_archive(tmp_path, count=1, empty=False):
    tasks = [{"code": f"sh.{600000 + index}", "year": 2021} for index in range(count)]
    plan = {"scopeSha256": "a" * 64, "tasks": tasks, "start": "2020-08-25", "end": "2026-08-24"}
    daily = {"sha256": "c" * 64}
    store = ActionStore(tmp_path / "actions.sqlite")
    store.initialize(plan)
    run = store.begin_run({"scopeSha256": plan["scopeSha256"], "dailyInput": daily,
                           "sourceIdentity": {"provider": "BaoStock", "providerVersion": "0.9.3", "adapterSha256": "b" * 64}})
    request = store.start_request(tasks[0], run)
    frame = pd.DataFrame(columns=sorted(REQUIRED_FIELDS))
    if not empty:
        row = {field: "" for field in REQUIRED_FIELDS}
        row.update(code=tasks[0]["code"], dividOperateDate="2021-07-01", dividCashPsBeforeTax="0.6",
                   dividCashPsAfterTax="0.54或0.6", dividCashStock="10派6元（含税）")
        frame = pd.DataFrame([row])
    frame.attrs["request"] = {**tasks[0], "yearType": "operate"}
    store.save_response(request, frame)
    store.finish_run(run)
    return store, plan, daily, request, run


def test_complete_raw_capture_is_not_economic_admission(tmp_path):
    store, plan, daily, _, _ = fixture_archive(tmp_path)
    result = audit_action_archive(store.path, plan, daily)
    assert result["state"] == "capture-ready"
    assert result["tasksComplete"] and result["archiveIntegrityPass"]
    assert result["counts"]["rawResponsesChecked"] == result["counts"]["currentProjectionsChecked"] == 1
    assert result["unresolvedFieldCounts"]["ambiguous:dividCashPsAfterTax"] == 1
    assert len(result["requestIndexSha256"]) == 64
    assert result["ledgerReady"] is result["investorTaxVerified"] is False


def test_queried_empty_year_is_verified_and_pending_tasks_remain_incomplete(tmp_path):
    store, plan, daily, _, _ = fixture_archive(tmp_path, count=2, empty=True)
    result = audit_action_archive(store.path, plan, daily)
    assert result["state"] == "capture-incomplete"
    assert result["counts"]["queriedEmptyYears"] == 1
    assert result["tasks"] == {"succeeded": 1, "pending": 1}
    assert result["archiveIntegrityPass"] and not result["captureReady"]


def test_deleted_task_cannot_turn_partial_capture_into_complete(tmp_path):
    store, plan, daily, _, _ = fixture_archive(tmp_path, count=2)
    with store.connect() as connection:
        connection.execute("DELETE FROM action_tasks WHERE status='pending'")
    assert store.status()["state"] == "source-capture-complete"
    result = audit_action_archive(store.path, plan, daily)
    assert not result["tasksComplete"] and not result["captureReady"]
    assert result["problems"]["counts"]["missing_planned_task"] == 1


@pytest.mark.parametrize("mutation,reason", [
    ("UPDATE action_requests SET raw_json='{}'", "raw_response_invalid"),
    ("UPDATE action_requests SET row_count=2", "raw_response_invalid"),
    ("UPDATE action_tasks SET active_request_id='wrong-request'", "task_request_ownership"),
    ("UPDATE action_tasks SET attempts=2", "attempt_history"),
    ("DELETE FROM action_events", "projection_row_indices"),
    ("UPDATE action_events SET normalized_json=json_set(normalized_json,'$.gross_cash_per_share','600')", "projection_invalid"),
    ("UPDATE action_events SET normalized_json=json_set(normalized_json,'$.investor_tax_verified',json('true'))", "projection_invalid"),
    ("UPDATE action_runs SET input_evidence_json=json_set(input_evidence_json,'$.dailyInput.sha256','different')", "run_provenance"),
])
def test_storage_or_provenance_defect_fails_closed(tmp_path, mutation, reason):
    store, plan, daily, _, _ = fixture_archive(tmp_path)
    with store.connect() as connection:
        connection.execute(mutation)
    result = audit_action_archive(store.path, plan, daily)
    assert result["state"] == "capture-invalid" and not result["captureReady"]
    assert result["problems"]["counts"][reason] >= 1


def test_changed_source_scope_is_not_accepted(tmp_path):
    store, plan, daily, _, _ = fixture_archive(tmp_path)
    plan = {**plan, "end": "2025-08-24"}
    result = audit_action_archive(store.path, plan, daily)
    assert result["problems"]["counts"]["scope_mismatch"] == 1
    assert not result["captureReady"]


def test_legacy_projection_is_explicitly_unchecked_and_never_rewritten(tmp_path):
    store, plan, daily, _, _ = fixture_archive(tmp_path)
    with store.connect() as connection:
        connection.execute("UPDATE action_events SET normalized_json=json_remove(normalized_json,'$.normalization_version')")
        before = connection.execute("SELECT normalized_json FROM action_events").fetchone()[0]
    result = audit_action_archive(store.path, plan, daily)
    assert result["captureReady"] and result["counts"]["legacyProjectionsUnchecked"] == 1
    assert result["counts"]["rawResponsesChecked"] == 1
    with store.connect(readonly=True) as connection:
        assert connection.execute("SELECT normalized_json FROM action_events").fetchone()[0] == before


def test_audit_observes_one_snapshot_while_writer_commits(tmp_path, monkeypatch):
    store, plan, daily, _, _ = fixture_archive(tmp_path)
    original = audit_module._audit_tasks
    def after_snapshot(connection, expected, problems):
        with store.connect() as writer:
            writer.execute("DELETE FROM action_events")
        return original(connection, expected, problems)
    monkeypatch.setattr(audit_module, "_audit_tasks", after_snapshot)
    first = audit_action_archive(store.path, plan, daily)
    assert first["captureReady"] and first["counts"]["currentProjectionsChecked"] == 1
    monkeypatch.setattr(audit_module, "_audit_tasks", original)
    second = audit_action_archive(store.path, plan, daily)
    assert not second["captureReady"]
    assert second["problems"]["counts"]["projection_row_indices"] == 1


def test_cli_writes_new_evidence_and_refuses_overwrite(tmp_path, monkeypatch):
    store, plan, daily, _, _ = fixture_archive(tmp_path)
    config = ActionConfig("fixture", "market.json", "actions.sqlite")
    monkeypatch.setattr(ActionConfig, "from_json", lambda _: config)
    monkeypatch.setattr("qforge.actions.cli.action_plan", lambda *_: plan)
    monkeypatch.setattr("qforge.actions.cli.admit_action_input", lambda *_: daily)
    args = argparse.Namespace(config="actions.json", action_command="audit", output="audit.json")
    assert run_action_command(args, tmp_path) == 0
    before = (tmp_path / "audit.json").read_bytes()
    assert json.loads(before)["captureReady"]
    assert run_action_command(args, tmp_path) == 2
    assert (tmp_path / "audit.json").read_bytes() == before
