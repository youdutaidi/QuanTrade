"""Export adjusted-price features and raw prices, not a total-return ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qforge.marketdata.config import MarketDataConfig
from qforge.marketdata.panel import export_research_panel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    config_path = Path(args.config)
    config = MarketDataConfig.from_json(config_path if config_path.is_absolute() else root / config_path)
    output = Path(args.output)
    output = output if output.is_absolute() else root / output
    payload = export_research_panel(root / config.database_path, output, config.start, config.end, config.adjustflag)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
