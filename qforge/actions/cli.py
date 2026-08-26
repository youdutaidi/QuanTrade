"""CLI for lossless annual dividends; preview and status never contact the source."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import ActionConfig
from .planning import action_plan
from .service import download_actions
from .store import ActionStore


def register_action_commands(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("actions", help="local raw dividend archive, not certified P&L")
    actions = parser.add_subparsers(dest="action_command", required=True)
    for name in ("plan", "download", "status"):
        action = actions.add_parser(name)
        action.add_argument("--config", required=True)
        if name == "download":
            action.add_argument("--max-tasks", type=int, default=None)
        if name == "plan":
            action.add_argument("--preview", action="store_true", required=True,
                                help="read lifecycle coverage only; no network or database changes")
            action.add_argument("--include-tasks", action="store_true")


def run_action_command(args: argparse.Namespace, root: Path) -> int:
    config = ActionConfig.from_json(root / args.config)
    try:
        if args.action_command == "plan":
            result = action_plan(config, root)
            if not args.include_tasks:
                result.pop("tasks")
        elif args.action_command == "download":
            result = download_actions(config, root, args.max_tasks)
        else:
            result = ActionStore(root / config.database_path).status()
    except (ValueError, FileNotFoundError, RuntimeError) as error:
        print(json.dumps({"state": "not-admitted-or-failed", "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
