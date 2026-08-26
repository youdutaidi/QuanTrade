"""Workflow boundary for completed inputs; development never loads holdout rows."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from qforge.marketdata.admission import verify_completed_panel
from qforge.marketdata.config import MarketDataConfig
from qforge.marketdata.export import file_sha256

from .specification import StudySpec


def verify_study_inputs(spec: StudySpec, root: Path, frozen_plan: Path) -> dict:
    spec.validate()
    plan = json.loads(frozen_plan.read_text(encoding="utf-8"))
    ids = [candidate.candidate_id for candidate in spec.candidates()]
    if plan.get("configSha256") != spec.sha256 or [row["candidateId"] for row in plan.get("candidates", [])] != ids:
        raise ValueError("study specification differs from the pre-outcome frozen plan")
    values = spec.values
    config = MarketDataConfig.from_json(root / values["data_config"])
    if config.start != values["periods"]["discovery"][0] or config.end != values["periods"]["holdout"][1]:
        raise ValueError("study dates do not match admitted data dates")
    if config.adjustflag != 3 or config.security_types != ["1"] or values["benchmark"] not in config.benchmark_codes:
        raise ValueError("study requires raw A-share data and its frozen benchmark")
    evidence = verify_completed_panel(root / values["data_manifest"], config)
    return {**evidence, "studySha256": spec.sha256, "frozenPlanSha256": file_sha256(frozen_plan)}


def load_development_frame(spec: StudySpec, root: Path, frozen_plan: Path) -> tuple[pd.DataFrame, dict]:
    evidence = verify_study_inputs(spec, root, frozen_plan)
    end = pd.Timestamp(spec.values["periods"]["folds"][-1]["test"][1])
    start = pd.Timestamp(spec.values["periods"]["discovery"][0])
    path = Path(evidence["panel"])
    # Predicate pushdown: holdout values never enter the strategy dataframe.
    frame = pd.read_parquet(path, filters=[("date", ">=", start), ("date", "<=", end)])
    if frame.empty or frame["date"].min() < start or frame["date"].max() > end:
        raise ValueError("invalid development data window")
    if file_sha256(path) != evidence["sha256"]:
        raise ValueError("research panel changed while loading development inputs")
    return frame, {**evidence, "loadedRows": len(frame), "loadedThrough": str(end.date()), "holdoutLoaded": False}
