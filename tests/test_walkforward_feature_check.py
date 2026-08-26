import json
import sqlite3
from pathlib import Path

import pytest

from qforge.marketdata.config import MarketDataConfig
from qforge.walkforward.feature_check import run_feature_check
from qforge.walkforward.inputs import load_development_reference
from qforge.walkforward.replay_inputs import prepare_replay_inputs
from qforge.walkforward.specification import StudySpec
from qforge.walkforward.synthetic_market import synthetic_market


@pytest.fixture
def feature_input(tmp_path, monkeypatch):
    spec = StudySpec.from_json(Path(__file__).resolve().parents[1] / "configs/walk_forward.json")
    frame, calendar, securities, _ = synthetic_market(spec)
    evidence = {"state": "verified-input", "loadedRows": len(frame), "holdoutLoaded": False, "studySha256": spec.sha256}
    monkeypatch.setattr("qforge.walkforward.feature_check.load_development_frame", lambda *_: (frame.copy(), evidence))
    monkeypatch.setattr("qforge.walkforward.feature_check.load_development_reference",
                        lambda *_: (calendar, securities, {"referenceSha256": "fixture"}))
    return spec, tmp_path, frame, evidence


def test_feature_workflow_checks_all_frozen_settings_without_a_portfolio(feature_input):
    spec, root, _, _ = feature_input
    output = root / "feature-evidence"
    result = run_feature_check(spec, root, root / "plan.json", output)
    assert result["state"] == "development-features-checked"
    assert result["signalSettings"] == 16 and result["candidateCount"] == 144
    assert result["stockSymbols"] == 3 and result["sessions"] == 420
    assert all(item["finiteScores"] > 0 for item in result["scores"])
    assert result["holdoutLoaded"] is result["strategyOutcomesComputed"] is result["verifiedStrategy"] is False
    assert not (root / "research/data/qforge_walkforward.sqlite").exists()
    before = (output / "result.json").read_bytes()
    with pytest.raises(FileExistsError):
        run_feature_check(spec, root, root / "plan.json", output)
    assert (output / "result.json").read_bytes() == before


def test_missing_listed_bar_stops_before_feature_computation(feature_input, monkeypatch):
    spec, root, frame, evidence = feature_input
    monkeypatch.setattr("qforge.walkforward.feature_check.load_development_frame", lambda *_: (frame.iloc[1:], evidence))
    calls = []
    monkeypatch.setattr("qforge.walkforward.feature_check.build_score_cache", lambda *_: calls.append(True))
    with pytest.raises(ValueError, match="missing listed bar"):
        run_feature_check(spec, root, root / "plan.json", root / "missing-row")
    assert calls == []


def test_ineligible_finite_score_is_rejected(feature_input, monkeypatch):
    from qforge.walkforward.replay_inputs import build_score_cache
    spec, root, _, _ = feature_input
    def invalid_scores(inputs, study):
        scores = build_score_cache(inputs, study)
        next(iter(scores.values())).iloc[0, 0] = 1.0
        return scores
    monkeypatch.setattr("qforge.walkforward.feature_check.build_score_cache", invalid_scores)
    with pytest.raises(ValueError, match="ineligible finite"):
        run_feature_check(spec, root, root / "plan.json", root / "bad-score")


def test_reference_loader_excludes_holdout_calendar_and_records_identity(tmp_path):
    spec = StudySpec.from_json(Path(__file__).resolve().parents[1] / "configs/walk_forward.json")
    config = MarketDataConfig.from_json(Path(__file__).resolve().parents[1] / spec.values["data_config"])
    config_path = tmp_path / spec.values["data_config"]
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps(config.as_dict()))
    database = tmp_path / config.database_path
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE trade_calendar(calendar_date TEXT,is_trading_day INTEGER)")
        connection.execute("CREATE TABLE securities(code TEXT,ipo_date TEXT,out_date TEXT,security_type TEXT)")
        connection.executemany("INSERT INTO trade_calendar VALUES(?,?)", [("2020-08-25", 1), ("2025-08-22", 1), ("2025-08-25", 1)])
        connection.execute("INSERT INTO securities VALUES('sh.600000','1999-11-10',NULL,'1')")
    calendar, stocks, evidence = load_development_reference(spec, tmp_path)
    assert calendar == ["2020-08-25", "2025-08-22"]
    assert stocks["code"].tolist() == ["sh.600000"]
    assert evidence["referenceThrough"] == "2025-08-24"
    assert len(evidence["referenceSha256"]) == 64
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE trade_calendar SET is_trading_day=0 WHERE calendar_date='2025-08-25'")
    assert load_development_reference(spec, tmp_path)[2] == evidence


def test_suspended_liquidity_nulls_survive_and_cannot_create_eligibility(feature_input):
    spec, _, frame, _ = feature_input
    _, calendar, securities, _ = synthetic_market(spec)
    symbol = securities.iloc[0]["code"]
    mask = frame["symbol"].eq(symbol) & frame["date"].eq(calendar[401])
    frame.loc[mask, ["trade_status", "volume", "amount"]] = [0, float("nan"), float("nan")]
    inputs = prepare_replay_inputs(frame, calendar, securities, spec)
    assert inputs.fields["volume"].loc[calendar[401], symbol] != inputs.fields["volume"].loc[calendar[401], symbol]
    assert inputs.fields["amount"].loc[calendar[401], symbol] != inputs.fields["amount"].loc[calendar[401], symbol]
    assert not inputs.eligible.loc[calendar[401]:, symbol].any()
    assert inputs.capacity.loc[calendar[402], symbol] == 0


@pytest.mark.parametrize("field", ["volume", "amount"])
def test_tradable_liquidity_null_remains_an_error(feature_input, field):
    spec, _, frame, _ = feature_input
    _, calendar, securities, _ = synthetic_market(spec)
    frame.loc[0, field] = float("nan")
    with pytest.raises(ValueError, match="missing tradable"):
        prepare_replay_inputs(frame, calendar, securities, spec)


def test_suspended_negative_liquidity_remains_an_error(feature_input):
    spec, _, frame, _ = feature_input
    _, calendar, securities, _ = synthetic_market(spec)
    frame.loc[0, ["trade_status", "amount"]] = [0, -1]
    with pytest.raises(ValueError, match="negative listed"):
        prepare_replay_inputs(frame, calendar, securities, spec)
