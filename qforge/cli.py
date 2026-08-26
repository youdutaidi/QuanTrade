"""Thin command-line entrypoint for Q-Forge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import BacktestConfig
from .actions.cli import register_action_commands, run_action_command
from .demo import create_demo
from .factors import factor_catalog
from .marketdata.cli import register_market_commands, run_market_command
from .minute.cli import register_minute_commands, run_minute_command
from .pipeline import run_experiment
from .walkforward.cli import register_walkforward_commands, run_walkforward_command


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="qforge", description="Local point-in-time factor backtesting")
    root.add_argument("--root", default=".", help="repository root")
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run one JSON experiment config")
    run.add_argument("--config", required=True)
    commands.add_parser("demo", help="generate deterministic data and run a smoke test")
    catalog = commands.add_parser("catalog", help="list implemented factor functions")
    catalog.add_argument("--json", action="store_true")
    register_minute_commands(commands)
    register_market_commands(commands)
    register_walkforward_commands(commands)
    register_action_commands(commands)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "minute":
        return run_minute_command(args, root)
    if args.command == "market":
        return run_market_command(args, root)
    if args.command == "walkforward":
        return run_walkforward_command(args, root)
    if args.command == "actions":
        return run_action_command(args, root)
    if args.command == "catalog":
        _print_catalog(args.json)
        return 0
    config_path = Path(args.config) if args.command == "run" else create_demo(root)
    if not config_path.is_absolute():
        config_path = root / config_path
    config = BacktestConfig.from_json(config_path)
    payload = run_experiment(config, root)
    print(json.dumps(_summary(payload), ensure_ascii=False, indent=2))
    return 0


def _print_catalog(as_json: bool) -> None:
    catalog = factor_catalog()
    if as_json:
        print(json.dumps(catalog, ensure_ascii=False, indent=2))
        return
    for item in catalog:
        print(f"{item['name']:<24} {item['description']}")


def _summary(payload: dict[str, object]) -> dict[str, object]:
    leader = payload["ranking"][0] if payload["ranking"] else None
    return {
        "experimentId": payload["experimentId"],
        "factorCount": payload["factorCount"],
        "leader": leader,
        "artifacts": payload["artifacts"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
