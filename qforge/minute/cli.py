"""CLI registration for local minute-data and paper-trading commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import MinuteConfig
from .engine import download_baostock, initialize_minute_store, run_minute_backtest
from .store import MinuteStore


def register_minute_commands(commands: argparse._SubParsersAction) -> None:
    minute = commands.add_parser("minute", help="local minute data and paper trading")
    actions = minute.add_subparsers(dest="minute_command", required=True)
    for name, help_text in [
        ("init", "initialize the local SQLite database"),
        ("download", "download BaoStock minute bars"),
        ("backtest", "run the next-bar paper replay"),
        ("status", "show local database status"),
    ]:
        action = actions.add_parser(name, help=help_text)
        action.add_argument("--config", required=True)


def run_minute_command(args: argparse.Namespace, root: Path) -> int:
    path = Path(args.config)
    config = MinuteConfig.from_json(path if path.is_absolute() else root / path)
    if args.minute_command == "init":
        payload = initialize_minute_store(config, root)
    elif args.minute_command == "download":
        payload = download_baostock(config, root)
    elif args.minute_command == "backtest":
        payload = run_minute_backtest(config, root)
    else:
        store = MinuteStore(root / config.database_path)
        payload = store.status()
    print(json.dumps(_summary(payload), ensure_ascii=False, indent=2))
    return 0


def _summary(payload: dict[str, object]) -> dict[str, object]:
    summary = {
        key: payload[key]
        for key in ("state", "experimentId", "runId", "database", "metrics", "ledger", "artifacts")
        if key in payload
    }
    return summary or payload
