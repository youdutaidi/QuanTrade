"""Requery a deterministic stock sample and compare it with local rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qforge.marketdata.config import MarketDataConfig
from qforge.marketdata.verify import verify_source_sample


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--sample-size", type=int, default=20)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    config_path = Path(args.config)
    config = MarketDataConfig.from_json(config_path if config_path.is_absolute() else root / config_path)
    payload = verify_source_sample(config, root, args.sample_size)
    output = Path(args.output)
    output = output if output.is_absolute() else root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"sampleSize": payload["sampleSize"], "allPass": payload["allPass"]}))


if __name__ == "__main__":
    main()
