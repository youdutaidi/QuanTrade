from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from qforge.marketdata.config import MarketDataConfig
from qforge.marketdata.export import file_sha256
from qforge.walkforward.inputs import load_development_frame, verify_study_inputs
from qforge.walkforward.specification import StudySpec


@pytest.fixture
def fixture_input(tmp_path):
    root = Path(__file__).resolve().parents[1]
    spec = StudySpec.from_json(root / "configs/walk_forward.json")
    config = MarketDataConfig.from_json(root / spec.values["data_config"])
    path = tmp_path / "panel.parquet"
    frame = pd.DataFrame({"date": pd.to_datetime(["2024-01-02", "2026-01-02"]),
                          "symbol": ["sh.600000", "sh.600000"], "close": [1.0, 99999.0]})
    frame.to_parquet(path, index=False)
    config_path = tmp_path / spec.values["data_config"]
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps(config.as_dict()))
    manifest = tmp_path / spec.values["data_manifest"]
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"state": "ready", "errors": [], "config": config.as_dict(),
                                   "audit": {"dataReady": True}, "verification": {"allPass": True, "sampleSize": 1},
                                   "panel": {"output": str(path), "sha256": file_sha256(path), "rows": 2}}))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"configSha256": spec.sha256,
                               "candidates": [{"candidateId": candidate.candidate_id} for candidate in spec.candidates()]}))
    return spec, tmp_path, plan, manifest, path


def test_development_loader_filters_holdout_before_dataframe_creation(fixture_input, monkeypatch):
    spec, root, plan, _, _ = fixture_input
    original = pd.read_parquet
    filters = []

    def observed(*args, **kwargs):
        filters.extend(kwargs["filters"])
        return original(*args, **kwargs)

    monkeypatch.setattr(pd, "read_parquet", observed)
    frame, evidence = load_development_frame(spec, root, plan)
    assert frame["close"].tolist() == [1.0]
    assert ("date", "<=", pd.Timestamp("2025-08-24")) in filters
    assert evidence["holdoutLoaded"] is False


@pytest.mark.parametrize("failure", ["incomplete", "changed_panel", "changed_spec", "missing_source_replay", "wrong_scope"])
def test_input_admission_fails_closed(fixture_input, failure):
    spec, root, plan, manifest, panel = fixture_input
    payload = json.loads(manifest.read_text())
    if failure == "incomplete":
        payload["state"] = "incomplete"
    elif failure == "changed_panel":
        pd.DataFrame({"x": [1]}).to_parquet(panel)
    elif failure == "changed_spec":
        plan.write_text(json.dumps({"configSha256": "wrong", "candidates": []}))
    elif failure == "missing_source_replay":
        payload["verification"]["sampleSize"] = 0
    else:
        payload["config"]["adjustflag"] = 2
    manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        verify_study_inputs(spec, root, plan)


def test_loader_rejects_file_replacement_during_load(fixture_input, monkeypatch):
    spec, root, plan, _, panel = fixture_input
    original = pd.read_parquet

    def replace_after_read(*args, **kwargs):
        frame = original(*args, **kwargs)
        pd.DataFrame({"x": [1]}).to_parquet(panel)
        return frame

    monkeypatch.setattr(pd, "read_parquet", replace_after_read)
    with pytest.raises(ValueError, match="changed while loading"):
        load_development_frame(spec, root, plan)
