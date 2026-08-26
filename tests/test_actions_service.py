import json
import sqlite3

import pandas as pd
import pytest

from qforge.actions.config import ActionConfig
from qforge.actions.normalization import REQUIRED_FIELDS
from qforge.actions.service import download_actions
from qforge.actions.store import ActionStore
from qforge.marketdata.session import FileLock


def setup_source(tmp_path, monkeypatch):
    config = ActionConfig("fixture", "market.json", "actions.sqlite", batch_pause_seconds=0)
    tasks = [{"code": "sh.600000", "year": year} for year in (2020, 2021, 2022)]
    monkeypatch.setattr("qforge.actions.service.admit_action_input", lambda *_: {"kind": "synthetic"})
    monkeypatch.setattr("qforge.actions.service.action_plan", lambda *_: {"scopeSha256": "fixture", "tasks": tasks})
    monkeypatch.setattr("qforge.actions.service.capture_identity", lambda: {"provider": "fixture"})
    return config


def test_request_budget_resume_and_new_session_after_error(tmp_path, monkeypatch):
    config = setup_source(tmp_path, monkeypatch)
    calls, sessions = [], []
    class Provider:
        def __init__(self, **_):
            pass
        def __enter__(self):
            sessions.append("login")
            return self
        def __exit__(self, *_):
            sessions.append("logout")
        def dividends(self, code, year):
            calls.append(year)
            if len(calls) == 1:
                raise RuntimeError("fixture partial stream")
            frame = pd.DataFrame(columns=sorted(REQUIRED_FIELDS))
            frame.attrs["request"] = {"code": code, "year": year, "yearType": "operate"}
            return frame
    monkeypatch.setattr("qforge.actions.service.BaoStockMarketProvider", Provider)
    first = download_actions(config, tmp_path, max_tasks=2)
    assert first["attemptedTasks"] == 2 and first["failures"] == 1
    assert first["tasks"] == {"failed": 1, "pending": 1, "succeeded": 1}
    assert sessions == ["login", "logout", "login", "logout"]
    second = download_actions(config, tmp_path)
    assert calls == [2020, 2021, 2020, 2022]
    assert second["state"] == "source-capture-complete"
    assert second["requests"] == 4 and second["queriedEmptyYears"] == 3


def test_login_failure_does_not_consume_request_attempt(tmp_path, monkeypatch):
    config = setup_source(tmp_path, monkeypatch)
    class FailedProvider:
        def __init__(self, **_):
            pass
        def __enter__(self):
            raise RuntimeError("login failed fixture")
        def __exit__(self, *_):
            pass
    monkeypatch.setattr("qforge.actions.service.BaoStockMarketProvider", FailedProvider)
    with pytest.raises(RuntimeError, match="login failed"):
        download_actions(config, tmp_path, max_tasks=1)
    store = ActionStore(tmp_path / config.database_path)
    assert store.status()["requests"] == 0
    assert len(store.pending_tasks(1, None)) == 3


def test_job_lock_prevents_recovery_or_input_checks(tmp_path, monkeypatch):
    config = ActionConfig("fixture", "missing.json", "actions.sqlite")
    with FileLock(tmp_path / "actions.sqlite.job.lock"):
        with pytest.raises(RuntimeError, match="another process"):
            download_actions(config, tmp_path)
    assert not (tmp_path / "actions.sqlite").exists()


def test_active_daily_job_blocks_before_action_database_or_source(tmp_path):
    market = {"experiment_id": "fixture", "database_path": "market.sqlite", "start": "2020-01-01", "end": "2021-01-01"}
    (tmp_path / "market.json").write_text(json.dumps(market))
    with sqlite3.connect(tmp_path / "market.sqlite") as conn:
        conn.execute("CREATE TABLE market_download_runs(status TEXT)")
        conn.execute("INSERT INTO market_download_runs VALUES('running')")
    config = ActionConfig("fixture", "market.json", "actions.sqlite")
    with pytest.raises(ValueError, match="daily source job is still running"):
        download_actions(config, tmp_path)
    assert not (tmp_path / "actions.sqlite").exists()
