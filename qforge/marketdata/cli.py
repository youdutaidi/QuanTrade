"""CLI registration for the local point-in-time market database."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import MarketDataConfig
from .service import download_daily, download_reference, initialize_market_store, market_status


def register_market_commands(commands: argparse._SubParsersAction) -> None:
    market = commands.add_parser("market", help="local point-in-time market database")
    actions = market.add_subparsers(dest="market_command", required=True)
    for name, help_text in [
        ("init", "initialize the market SQLite database"),
        ("download-reference", "download calendar, security master, and universe audits"),
        ("status", "show local data inventory and checkpoints"),
    ]:
        action = actions.add_parser(name, help=help_text)
        action.add_argument("--config", required=True)
    daily = actions.add_parser("download-daily", help="download resumable daily bars and adjustment factors")
    daily.add_argument("--config", required=True)
    daily.add_argument("--max-tasks", type=int, default=None, help="bounded number of pending securities for this invocation")
    daily.add_argument("--recover", action="store_true", help="release tasks left running by an interrupted invocation")
    reset = actions.add_parser("reset-daily", help="delete only daily bars/factors and reset their checkpoints")
    reset.add_argument("--config", required=True)
    reset.add_argument("--confirm-qf-data-expansion", action="store_true", required=True)


def run_market_command(args: argparse.Namespace, root: Path) -> int:
    path = Path(args.config)
    config = MarketDataConfig.from_json(path if path.is_absolute() else root / path)
    if args.market_command == "init":
        payload = initialize_market_store(config, root)
    elif args.market_command == "download-reference":
        payload = download_reference(config, root)
    elif args.market_command == "download-daily":
        payload = download_daily(config, root, args.max_tasks, args.recover)
    elif args.market_command == "reset-daily":
        from .store import MarketDataStore

        store = MarketDataStore(root / config.database_path)
        store.initialize()
        payload = {"state": "daily-reset", **store.reset_daily_data(), **store.status()}
    else:
        payload = market_status(config, root)
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0
