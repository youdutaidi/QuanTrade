"""Real input/compute preflight; never selects candidates or evaluates a portfolio."""

from __future__ import annotations

import json
import resource
import sys
import time
from pathlib import Path

import numpy as np

from .inputs import load_development_frame, load_development_reference
from .replay_inputs import build_score_cache, prepare_replay_inputs, signal_key
from .specification import StudySpec


def run_feature_check(spec: StudySpec, root: Path, frozen_plan: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    frame, evidence = load_development_frame(spec, root, frozen_plan)
    calendar, securities, reference = load_development_reference(spec, root)
    loaded = time.perf_counter()
    inputs = prepare_replay_inputs(frame, calendar, securities, spec)
    del frame
    aligned = time.perf_counter()
    scores = build_score_cache(inputs, spec)
    computed = time.perf_counter()
    summaries = _score_summaries(scores, inputs, spec)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    payload = {**evidence, **reference, "state": "development-features-checked",
               "stockSymbols": inputs.listed.shape[1], "sessions": len(inputs.sessions),
               "firstSession": inputs.sessions[0], "lastSession": inputs.sessions[-1],
               "candidateCount": len(spec.candidates()), "signalSettings": len(scores), "scores": summaries,
               "timingSeconds": {"load": loaded - started, "align": aligned - loaded,
                                 "allScoreSettings": computed - aligned, "total": time.perf_counter() - started},
               "peakResidentBytes": peak if sys.platform == "darwin" else peak * 1024,
               "strategyOutcomesComputed": False, "verifiedStrategy": False,
               "claim": "real development signal input/compute check only; no economic return, selection or holdout"}
    with (output / "result.json").open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return payload


def _score_summaries(scores: dict, inputs, spec: StudySpec) -> list[dict]:
    if set(scores) != {signal_key(candidate) for candidate in spec.candidates()}:
        raise ValueError("score cache differs from the frozen signal settings")
    summaries = []
    for key, frame in scores.items():
        if not frame.index.equals(inputs.eligible.index) or not frame.columns.equals(inputs.eligible.columns):
            raise ValueError("score matrix axes differ from the eligible universe")
        values = frame.to_numpy(dtype=float)
        finite = np.isfinite(values)
        if np.isinf(values).any() or not finite.any() or (finite & ~inputs.eligible.to_numpy()).any():
            raise ValueError(f"invalid, empty or ineligible finite scores: {key}")
        summaries.append({"setting": list(key), "finiteScores": int(finite.sum()),
                          "sessionsWithScores": int(finite.any(axis=1).sum()),
                          "symbolsWithScores": int(finite.any(axis=0).sum())})
    return summaries
