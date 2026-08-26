"""Zero-network workflow joining frozen factors, execution, persistence and audit."""

from __future__ import annotations

import json
from pathlib import Path

from .ledger_audit import audit_ledger
from .replay import replay_candidate
from .replay_inputs import build_score_cache, prepare_replay_inputs, signal_key
from .specification import StudySpec
from .store import load_ledger, persist_ledger
from .synthetic_market import synthetic_market


def run_execution_demo(spec: StudySpec, root: Path, output: Path, all_candidates: bool = False) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    frame, calendar, securities, actions = synthetic_market(spec)
    inputs = prepare_replay_inputs(frame, calendar, securities, spec)
    scores = build_score_cache(inputs, spec)
    chosen = [item for item in spec.candidates() if all_candidates or
              (item.family == "short_reversal" and item.lookback == 5 and item.rebalance_days == 5 and item.top_n == 10)]
    database = root / "research/data/qforge_walkforward.sqlite"
    runs = []
    for candidate in chosen:
        result = replay_candidate(inputs, scores[signal_key(candidate)], candidate, spec,
                                  calendar[400], calendar[-1], actions)
        summary = save_execution_result(spec, result, database, output)
        runs.append(summary)
    payload = {"state": "synthetic-execution-verified", "marketOutcomesRead": False,
               "verifiedStrategy": False, "candidateCount": len(runs), "signalSettings": len(scores),
               "allLedgerReplaysPass": all(row["audit"]["allPass"] for row in runs),
               "studySha256": spec.sha256, "syntheticRows": len(frame), "runs": runs,
               "claim": "execution mechanics only; no market P&L, source coverage or strategy admission"}
    with (output / "result.json").open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return {key: value for key, value in payload.items() if key != "runs"}


def save_execution_result(spec, result, database, output):
    audit = audit_ledger(result["events"], spec.values["execution"])
    if not audit["allPass"] or not audit.get("allSessionsClosed"):
        raise ValueError(f"synthetic portfolio replay did not pass: {audit}")
    stored = persist_ledger(database, spec, result["events"], {**audit, "candidateId": result["candidateId"]})
    events, _ = load_ledger(database, stored["runId"])
    replayed = audit_ledger(events, spec.values["execution"])
    if not replayed["allPass"] or replayed.get("finalEquity") != audit["finalEquity"]:
        raise ValueError("persisted synthetic portfolio replay changed")
    summary = {**stored, "candidateId": result["candidateId"], "audit": replayed,
               "metrics": result["metrics"], "maxObservedStockWeight": result["maxObservedStockWeight"],
               "staleValuationSessions": result["staleValuationSessions"]}
    with (output / f"{result['candidateId']}.json").open("x", encoding="utf-8") as stream:
        json.dump({**summary, "decisions": result["decisions"]}, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return summary
