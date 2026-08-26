import argparse
import json

import pandas as pd
import pytest

import qforge.actions.terms_preview as preview_module
from qforge.actions.audit import audit_action_connection
from qforge.actions.cli import run_action_command
from qforge.actions.config import ActionConfig
from qforge.actions.store import ActionStore
from qforge.actions.terms_preview import preview_action_terms
from test_actions_terms import cash_row


def make_archive(tmp_path, extra_rows=(), pending=False):
    task = {"code": "sh.600000", "year": 2025}
    plan = {"scopeSha256": "a" * 64, "tasks": [task], "start": "2020-08-25", "end": "2026-08-24"}
    if pending:
        plan["tasks"].append({"code": "sh.600001", "year": 2025})
    daily = {"sha256": "c" * 64}
    store = ActionStore(tmp_path / "actions.sqlite")
    store.initialize(plan)
    run = store.begin_run({"scopeSha256": plan["scopeSha256"], "dailyInput": daily,
                           "sourceIdentity": {"provider": "BaoStock", "providerVersion": "0.9.3", "adapterSha256": "b" * 64}})
    request = store.start_request(task, run)
    row = cash_row(dividPlanDate="2025-06-20", dividRegistDate="2025-06-30",
                   dividOperateDate="2025-07-01", dividPayDate="2025-07-01")
    future = {**row, "dividPlanDate": "2025-08-25", "dividRegistDate": "2025-08-28",
              "dividOperateDate": "2025-08-29", "dividPayDate": "2025-08-29"}
    frame = pd.DataFrame([row, row.copy(), future, *extra_rows])
    frame.attrs["request"] = {**task, "yearType": "operate"}
    store.save_response(request, frame)
    store.finish_run(run)
    return store, plan, daily


def test_date_bounded_preview_merges_once_and_never_certifies_pnl(tmp_path):
    store, plan, daily = make_archive(tmp_path)
    report = preview_action_terms(store.path, plan, daily, "2020-08-25", "2025-08-24")
    assert report["archive"]["captureReady"]
    assert report["counts"]["sourceRowsInWindow"] == 2
    assert report["counts"]["eventGroups"] == report["counts"]["gross-source-consistent"] == 1
    assert report["counts"]["resolvedMultipleRowGroups"] == 1
    assert report["examples"][0]["terms"]["gross_cash_per_share"] == "0.6"
    assert all(item["exDate"] <= "2025-08-24" for item in report["examples"])
    assert not report["ledgerReady"] and not report["investorTaxVerified"]
    assert report["unlocatedSourceRows"] == 0 and len(report["groupIndexSha256"]) == 64


def test_archive_corruption_stops_before_interpretation(tmp_path, monkeypatch):
    store, plan, daily = make_archive(tmp_path)
    with store.connect() as connection:
        connection.execute("UPDATE action_requests SET raw_sha256='bad'")
    monkeypatch.setattr(preview_module, "_source_groups", lambda *_: pytest.fail("must not interpret corrupted rows"))
    with pytest.raises(ValueError, match="integrity admission"):
        preview_action_terms(store.path, plan, daily, "2020-08-25", "2025-08-24")


def test_unlocatable_dates_remain_explicitly_unresolved(tmp_path):
    row = cash_row(dividOperateDate="2025-02-30")
    store, plan, daily = make_archive(tmp_path, extra_rows=[row])
    report = preview_action_terms(store.path, plan, daily, "2020-08-25", "2025-08-24")
    assert report["unlocatedSourceRows"] == 1
    assert report["counts"]["eventGroups"] == 1
    assert report["ledgerReady"] is False


def test_partial_capture_can_be_previewed_but_not_promoted(tmp_path):
    store, plan, daily = make_archive(tmp_path, pending=True)
    report = preview_action_terms(store.path, plan, daily, "2020-08-25", "2025-08-24")
    assert report["archive"]["archiveIntegrityPass"] and not report["archive"]["captureReady"]
    assert report["archive"]["tasks"]["pending"] == 1
    assert report["ledgerReady"] is False


def test_audit_and_terms_share_one_wal_snapshot(tmp_path, monkeypatch):
    store, plan, daily = make_archive(tmp_path)
    original = preview_module.audit_action_connection
    def concurrent_change(*args):
        result = original(*args)
        with store.connect() as writer:
            writer.execute("UPDATE action_requests SET raw_json='{}'")
        return result
    monkeypatch.setattr(preview_module, "audit_action_connection", concurrent_change)
    first = preview_action_terms(store.path, plan, daily, "2020-08-25", "2025-08-24")
    assert first["counts"]["eventGroups"] == 1
    with pytest.raises(ValueError, match="integrity admission"):
        preview_action_terms(store.path, plan, daily, "2020-08-25", "2025-08-24")


def test_connection_audit_requires_transaction(tmp_path):
    store, plan, daily = make_archive(tmp_path)
    with store.connect(readonly=True) as connection:
        with pytest.raises(ValueError, match="explicit read transaction"):
            audit_action_connection(connection, store.path, plan, daily)


@pytest.mark.parametrize("start,end", [("20200825", "2025-08-24"), ("2020-08-24", "2025-08-24"),
                                     ("2025-08-25", "2025-08-24")])
def test_invalid_preview_window_fails(tmp_path, start, end):
    store, plan, daily = make_archive(tmp_path)
    with pytest.raises(ValueError):
        preview_action_terms(store.path, plan, daily, start, end)


def test_terms_cli_report_is_immutable(tmp_path, monkeypatch):
    _, plan, daily = make_archive(tmp_path)
    config = ActionConfig("fixture", "market.json", "actions.sqlite")
    monkeypatch.setattr(ActionConfig, "from_json", lambda _: config)
    monkeypatch.setattr("qforge.actions.cli.action_plan", lambda *_: plan)
    monkeypatch.setattr("qforge.actions.cli.admit_action_input", lambda *_: daily)
    args = argparse.Namespace(config="actions.json", action_command="terms", output="terms.json",
                              start="2020-08-25", end="2025-08-24")
    assert run_action_command(args, tmp_path) == 0
    before = (tmp_path / "terms.json").read_bytes()
    assert json.loads(before)["state"] == "gross-terms-preview-only"
    assert run_action_command(args, tmp_path) == 2
    assert (tmp_path / "terms.json").read_bytes() == before
