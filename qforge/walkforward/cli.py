"""Preparation commands. Market-outcome execution requires a separate data gate."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from .specification import StudySpec
from .demo import run_ledger_demo
from .execution_demo import run_execution_demo
from .feature_check import run_feature_check
from .inputs import verify_study_inputs


def register_walkforward_commands(commands: argparse._SubParsersAction) -> None:
    group = commands.add_parser("walkforward", help="frozen point-in-time walk-forward research")
    actions = group.add_subparsers(dest="walkforward_command", required=True)
    plan = actions.add_parser("plan", help="validate and print the frozen candidate plan without reading market outcomes")
    plan.add_argument("--config", required=True)
    plan.add_argument("--output", help="optional new immutable plan artifact; refuses overwrite")
    preflight = actions.add_parser("preflight", help="verify completed data and frozen plan without reading outcomes")
    preflight.add_argument("--config", required=True)
    preflight.add_argument("--plan", required=True)
    demo = actions.add_parser("ledger-demo", help="persist and independently replay a zero-network synthetic account")
    demo.add_argument("--config", required=True)
    demo.add_argument("--output", required=True, help="new evidence directory; refuses overwrite")
    execution = actions.add_parser("execution-demo", help="zero-network frozen-factor to account execution and independent replay")
    execution.add_argument("--config", required=True)
    execution.add_argument("--output", required=True)
    execution.add_argument("--all-candidates", action="store_true", help="exercise all 144 frozen candidates on synthetic bars only")
    features = actions.add_parser("feature-check", help="real development input and frozen-factor compute preflight, no portfolio returns")
    features.add_argument("--config", required=True)
    features.add_argument("--plan", required=True)
    features.add_argument("--output", required=True, help="new evidence directory; refuses overwrite")


def run_walkforward_command(args: argparse.Namespace, root: Path) -> int:
    spec = StudySpec.from_json(root / args.config)
    if args.walkforward_command == "preflight":
        return _preflight(spec, root, root / args.plan)
    if args.walkforward_command == "ledger-demo":
        print(json.dumps(run_ledger_demo(spec, root, root / args.output), ensure_ascii=False, indent=2))
        return 0
    if args.walkforward_command == "execution-demo":
        payload = run_execution_demo(spec, root, root / args.output, args.all_candidates)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.walkforward_command == "feature-check":
        payload = run_feature_check(spec, root, root / args.plan, root / args.output)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    candidates = spec.candidates()
    payload = {
        "experimentId": spec.values["experiment_id"], "configSha256": spec.sha256,
        "state": "preparation-only", "marketOutcomesRead": False, "verifiedStrategy": False,
        "candidateCount": len(candidates), "familyCounts": dict(Counter(item.family for item in candidates)),
        "periods": spec.values["periods"],
        "candidates": [{"candidateId": item.candidate_id, **asdict(item)} for item in candidates],
        "scope": "frozen factor definitions and order primitives; portfolio and economic P&L verification pending",
    }
    if args.output:
        path = root / args.output
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as output:
            json.dump(payload, output, ensure_ascii=False, indent=2, allow_nan=False)
    summary = {key: value for key, value in payload.items() if key != "candidates"}
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


def _preflight(spec: StudySpec, root: Path, plan: Path) -> int:
    try:
        payload = verify_study_inputs(spec, root, plan)
    except (OSError, ValueError, KeyError) as error:
        print(json.dumps({"state": "not-admitted", "error": str(error), "marketOutcomesRead": False}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({**payload, "marketOutcomesRead": False}, ensure_ascii=False, indent=2))
    return 0
