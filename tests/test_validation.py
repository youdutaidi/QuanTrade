from qforge.validation import StrategyEvidence, ValidationPolicy, assess_strategy, build_registry


def policy() -> ValidationPolicy:
    return ValidationPolicy(
        policyVersion="test", minimumAnnualizedReturn=1.0, minimumSharpe=1.5,
        maximumDrawdown=-0.35, minimumDataYears=5, minimumOutOfSampleYears=1,
        minimumWalkForwardFolds=3, minimumForwardPaperDays=60,
        requirePointInTimeUniverse=True, requireNoLookaheadTest=True,
        requireTransactionCosts=True, requireCorporateActions=True,
        requireIndependentReplay=True, requireMultipleTestingControl=True,
    )


def evidence(**changes: object) -> StrategyEvidence:
    values = dict(
        strategyId="verified", label="Verified", timeframe="daily",
        annualizedReturn=1.2, sharpe=1.8, maxDrawdown=-0.25, dataYears=8,
        outOfSampleYears=2, walkForwardFolds=4, forwardPaperDays=80,
        pointInTimeUniverse=True, noLookaheadTest=True, transactionCosts=True,
        corporateActions=True, independentReplay=True, multipleTestingControl=True,
        evidencePath="evidence.json",
    )
    values.update(changes)
    return StrategyEvidence(**values)


def test_complete_evidence_is_verified() -> None:
    result = assess_strategy(evidence(), policy())
    assert result["status"] == "verified"
    assert all(check["passed"] for check in result["checks"])


def test_high_return_alone_is_rejected() -> None:
    result = assess_strategy(evidence(annualizedReturn=3.0, pointInTimeUniverse=False), policy())
    assert result["status"] == "rejected"
    assert not next(check for check in result["checks"] if check["key"] == "pointInTimeUniverse")["passed"]


def test_registry_never_promotes_partial_evidence() -> None:
    registry = build_registry([evidence(), evidence(strategyId="candidate", forwardPaperDays=0)], policy())
    assert registry["summary"] == {"assessed": 2, "verified": 1, "rejected": 1}
    assert [item["strategyId"] for item in registry["verified"]] == ["verified"]
