"""Machine-enforced admission policy for strategy evidence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationPolicy:
    policyVersion: str
    minimumAnnualizedReturn: float
    minimumSharpe: float
    maximumDrawdown: float
    minimumDataYears: float
    minimumOutOfSampleYears: float
    minimumWalkForwardFolds: int
    minimumForwardPaperDays: int
    requirePointInTimeUniverse: bool
    requireNoLookaheadTest: bool
    requireTransactionCosts: bool
    requireCorporateActions: bool
    requireIndependentReplay: bool
    requireMultipleTestingControl: bool

    @classmethod
    def from_json(cls, path: str | Path) -> "ValidationPolicy":
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass(frozen=True)
class StrategyEvidence:
    strategyId: str
    label: str
    timeframe: str
    annualizedReturn: float
    sharpe: float
    maxDrawdown: float
    dataYears: float
    outOfSampleYears: float
    walkForwardFolds: int
    forwardPaperDays: int
    pointInTimeUniverse: bool
    noLookaheadTest: bool
    transactionCosts: bool
    corporateActions: bool
    independentReplay: bool
    multipleTestingControl: bool
    evidencePath: str


def assess_strategy(evidence: StrategyEvidence, policy: ValidationPolicy) -> dict[str, object]:
    checks = [
        _minimum("年化收益", evidence.annualizedReturn, policy.minimumAnnualizedReturn, "annualizedReturn"),
        _minimum("Sharpe", evidence.sharpe, policy.minimumSharpe, "sharpe"),
        _minimum("数据年限", evidence.dataYears, policy.minimumDataYears, "dataYears"),
        _minimum("样本外年限", evidence.outOfSampleYears, policy.minimumOutOfSampleYears, "outOfSampleYears"),
        _minimum("滚动样本外折数", evidence.walkForwardFolds, policy.minimumWalkForwardFolds, "walkForwardFolds"),
        _minimum("前向模拟天数", evidence.forwardPaperDays, policy.minimumForwardPaperDays, "forwardPaperDays"),
        _maximum_drawdown(evidence.maxDrawdown, policy.maximumDrawdown),
        _required("历史点时股票池", evidence.pointInTimeUniverse, policy.requirePointInTimeUniverse, "pointInTimeUniverse"),
        _required("未来函数反证测试", evidence.noLookaheadTest, policy.requireNoLookaheadTest, "noLookaheadTest"),
        _required("真实交易摩擦", evidence.transactionCosts, policy.requireTransactionCosts, "transactionCosts"),
        _required("公司行动处理", evidence.corporateActions, policy.requireCorporateActions, "corporateActions"),
        _required("独立账本复算", evidence.independentReplay, policy.requireIndependentReplay, "independentReplay"),
        _required("多重检验控制", evidence.multipleTestingControl, policy.requireMultipleTestingControl, "multipleTestingControl"),
    ]
    passed = all(bool(check["passed"]) for check in checks)
    return {**asdict(evidence), "status": "verified" if passed else "rejected", "checks": checks}


def build_registry(evidence: list[StrategyEvidence], policy: ValidationPolicy) -> dict[str, object]:
    assessed = [assess_strategy(item, policy) for item in evidence]
    verified = [item for item in assessed if item["status"] == "verified"]
    rejected = [item for item in assessed if item["status"] == "rejected"]
    return {
        "policy": asdict(policy),
        "summary": {"assessed": len(assessed), "verified": len(verified), "rejected": len(rejected)},
        "verified": verified,
        "rejected": rejected,
    }


def _minimum(name: str, actual: float, required: float, key: str) -> dict[str, object]:
    return {"name": name, "key": key, "passed": actual >= required, "actual": actual, "required": required}


def _maximum_drawdown(actual: float, required: float) -> dict[str, object]:
    return {"name": "最大回撤", "key": "maxDrawdown", "passed": actual >= required, "actual": actual, "required": required}


def _required(name: str, actual: bool, required: bool, key: str) -> dict[str, object]:
    return {"name": name, "key": key, "passed": actual or not required, "actual": actual, "required": required}
