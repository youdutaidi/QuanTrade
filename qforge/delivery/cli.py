"""Thin local snapshot CLI. Remote release publication remains an explicit step."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from .capture import create_snapshot
from .recovery import restore_snapshot, verify_snapshot


def register_delivery_commands(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("archive", help="capture, verify or restore local data snapshots")
    actions = parser.add_subparsers(dest="archive_command", required=True)
    create = actions.add_parser("create")
    create.add_argument("--output", required=True, help="new directory outside the data allowlist")
    create.add_argument("--label", required=True)
    for name in ("verify", "restore"):
        action = actions.add_parser(name)
        action.add_argument("--bundle", required=True)
        action.add_argument("--sha256", required=True)
        if name == "restore":
            action.add_argument("--output", required=True, help="new, absent restore directory; never overwrites")


def run_delivery_command(args: argparse.Namespace, root: Path) -> int:
    try:
        if args.archive_command == "create":
            code = clean_code_identity(root)
            payload = create_snapshot(root, root / args.output, code, args.label)
        elif args.archive_command == "verify":
            payload = verify_snapshot(root / args.bundle, args.sha256)
        else:
            payload = restore_snapshot(root / args.bundle, args.sha256, root / args.output)
    except (ValueError, FileExistsError, FileNotFoundError) as error:
        print(json.dumps({"state": "refused", "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def clean_code_identity(root: Path) -> str:
    dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "qforge", "configs", "tests"], cwd=root).returncode
    untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "qforge", "configs", "tests"], cwd=root)
    if dirty or untracked:
        raise ValueError("commit admitted code/config/tests before capturing its data snapshot")
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
