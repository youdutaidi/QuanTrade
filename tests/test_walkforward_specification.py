from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from qforge.walkforward.specification import StudySpec


CONFIG = Path(__file__).resolve().parents[1] / "configs" / "walk_forward.json"


def test_frozen_grid_has_exactly_144_unique_candidates():
    spec = StudySpec.from_json(CONFIG)
    candidates = spec.candidates()
    assert len(candidates) == len({item.candidate_id for item in candidates}) == 144
    assert Counter(item.family for item in candidates) == {
        "residual_momentum": 54, "short_reversal": 27, "low_idiosyncratic_volatility": 18,
        "low_maximum_return": 18, "fixed_equal_composite": 27,
    }
    assert candidates == spec.candidates()


def test_spec_copy_cannot_mutate_frozen_source_or_identity():
    spec = StudySpec.from_json(CONFIG)
    before = spec.sha256
    copy = spec.values
    copy["selection"]["holdout_openings"] = 100
    assert spec.sha256 == before and spec.values["selection"]["holdout_openings"] == 1


def test_plan_cli_never_reads_market_data_and_refuses_overwrite(tmp_path, capsys):
    from qforge.cli import main
    output = tmp_path / "plan.json"
    args = ["walkforward", "plan", "--config", str(CONFIG), "--output", str(output)]
    assert main(args) == 0
    payload = json.loads(output.read_text())
    assert not payload["marketOutcomesRead"] and not payload["verifiedStrategy"]
    assert len(payload["candidates"]) == 144
    with pytest.raises(FileExistsError):
        main(args)
    assert "preparation-only" in capsys.readouterr().out


@pytest.mark.parametrize("change", ["overlap", "training_leak", "unlagged", "leverage", "duplicate", "concentration", "extra_holdout"])
def test_spec_rejects_unsafe_changes(change):
    values = StudySpec.from_json(CONFIG).values
    if change == "overlap":
        values["periods"]["holdout"][0] = "2025-08-24"
    elif change == "training_leak":
        values["periods"]["folds"][0]["train_end"] = "2022-08-25"
    elif change == "unlagged":
        values["signals"]["beta_lag"] = 0
    elif change == "leverage":
        values["execution"]["leverage"] = 2
    elif change == "duplicate":
        values["top_n"] = [10, 10, 50]
    elif change == "concentration":
        values["top_n"] = [5, 20, 50]
    else:
        values["selection"]["holdout_openings"] = 2
    with pytest.raises(ValueError):
        StudySpec(json.dumps(values)).validate()
