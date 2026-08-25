"""Write one recoverable JSON audit for the configured local market database."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qforge.marketdata.audit import audit_market_database
from qforge.marketdata.config import MarketDataConfig


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    config_path = Path(args.config)
    config = MarketDataConfig.from_json(config_path if config_path.is_absolute() else root / config_path)
    payload = audit_market_database(config, root)
    output = Path(args.output)
    output = output if output.is_absolute() else root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ["quickCheck", "tasksComplete", "integrityPass", "dataReady"]}))


if __name__ == "__main__":
    main()
