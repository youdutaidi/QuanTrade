"""CLI for lossless annual dividends; preview and status never contact the source."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from .config import ActionConfig
from .audit import audit_action_archive
from .planning import action_plan, admit_action_input
from .service import download_actions
from .store import ActionStore
from .terms_preview import preview_action_terms


def register_action_commands(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("actions", help="local raw dividend archive, not certified P&L")
    actions = parser.add_subparsers(dest="action_command", required=True)
    for name in ("plan", "download", "status", "audit", "terms"):
        action = actions.add_parser(name)
        action.add_argument("--config", required=True)
        if name == "download":
            action.add_argument("--max-tasks", type=int, default=None)
        if name == "plan":
            action.add_argument("--preview", action="store_true", required=True,
                                help="read lifecycle coverage only; no network or database changes")
            action.add_argument("--include-tasks", action="store_true")
        if name in {"audit", "terms"}:
            action.add_argument("--output", required=True, help="new immutable report; refuses overwrite")
        if name == "terms":
            action.add_argument("--start", required=True)
            action.add_argument("--end", required=True)
            action.add_argument("--include-unresolved", action="store_true",
                                help="include every unresolved in-window group and its checked raw rows")


def run_action_command(args: argparse.Namespace, root: Path) -> int:
    config = ActionConfig.from_json(root / args.config)
    try:
        if args.action_command == "plan":
            result = action_plan(config, root)
            if not args.include_tasks:
                result.pop("tasks")
        elif args.action_command == "download":
            result = download_actions(config, root, args.max_tasks)
        elif args.action_command == "audit":
            result = _audit(config, root, root / args.output)
        elif args.action_command == "terms":
            result = _terms(config, root, root / args.output, args.start, args.end, getattr(args, "include_unresolved", False))
        else:
            result = ActionStore(root / config.database_path).status()
    except (ValueError, OSError, RuntimeError, sqlite3.Error) as error:
        print(json.dumps({"state": "not-admitted-or-failed", "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if args.action_command == "audit" and not result["captureReady"] else 0


def _audit(config: ActionConfig, root: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"audit output already exists: {output}")
    plan = action_plan(config, root)
    daily_input = admit_action_input(config, root)
    result = audit_action_archive(root / config.database_path, plan, daily_input)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return result


def _terms(config: ActionConfig, root: Path, output: Path, start: str, end: str, include_unresolved: bool = False) -> dict:
    if output.exists():
        raise FileExistsError(f"terms output already exists: {output}")
    plan = action_plan(config, root)
    daily_input = admit_action_input(config, root)
    result = preview_action_terms(root / config.database_path, plan, daily_input, start, end, include_unresolved)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return result
