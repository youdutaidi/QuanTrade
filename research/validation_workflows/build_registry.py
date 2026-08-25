"""Build the website registry from frozen local strategy evidence."""

from __future__ import annotations

import json
from pathlib import Path

from qforge.validation import StrategyEvidence, ValidationPolicy, build_registry


ROOT = Path(__file__).resolve().parents[2]


def read_json(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def current_evidence() -> list[StrategyEvidence]:
    daily = read_json("app/data/backtest.json")
    factor = read_json("app/data/factor_backtest.json")
    minute = read_json("app/data/minute_system.json")
    robust = daily["strategies"][2]
    leader = factor["ranking"][0]
    return [
        StrategyEvidence(
            strategyId="AH-01-ROBUST-CANDIDATE", label=str(robust["label"]), timeframe="daily",
            annualizedReturn=float(robust["metrics"]["annualizedReturn"]), sharpe=float(robust["metrics"]["sharpe"]),
            maxDrawdown=float(robust["metrics"]["maxDrawdown"]), dataYears=1.0, outOfSampleYears=0.5,
            walkForwardFolds=1, forwardPaperDays=0, pointInTimeUniverse=False, noLookaheadTest=True,
            transactionCosts=True, corporateActions=False, independentReplay=False, multipleTestingControl=False,
            evidencePath="app/data/backtest.json",
        ),
        StrategyEvidence(
            strategyId="QF-DAILY-FACTOR-LEADER", label=str(leader["factor"]), timeframe="daily",
            annualizedReturn=float(leader["annualizedReturn"]), sharpe=float(leader["sharpe"]),
            maxDrawdown=float(leader["maxDrawdown"]), dataYears=1.0, outOfSampleYears=0.5,
            walkForwardFolds=1, forwardPaperDays=0, pointInTimeUniverse=False, noLookaheadTest=True,
            transactionCosts=True, corporateActions=True, independentReplay=False, multipleTestingControl=False,
            evidencePath="app/data/factor_backtest.json",
        ),
        StrategyEvidence(
            strategyId=str(minute["experimentId"]), label="Close Strength · Top 3", timeframe="5-minute",
            annualizedReturn=float(minute["metrics"]["totalReturn"]), sharpe=float(minute["metrics"]["sharpe"]),
            maxDrawdown=float(minute["metrics"]["maxDrawdown"]), dataYears=1.0, outOfSampleYears=0.5,
            walkForwardFolds=1, forwardPaperDays=0, pointInTimeUniverse=False, noLookaheadTest=True,
            transactionCosts=True, corporateActions=False, independentReplay=True, multipleTestingControl=True,
            evidencePath="app/data/minute_system.json",
        ),
    ]


def main() -> None:
    policy = ValidationPolicy.from_json(ROOT / "configs/validation_policy.json")
    registry = build_registry(current_evidence(), policy)
    target = ROOT / "app/data/validation_registry.json"
    target.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(registry["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
