# Q-Forge research contract

## Code-evolution record

```yaml
goal_id: QF-FACTOR-ENGINE-01
decision: Add a reusable daily cross-sectional factor engine without replacing the admitted price-strategy search baseline.
non_goals:
  - live order routing or broker integration
  - claiming that all 324 literature factors are computable from OHLCV alone
  - promising a 100 percent return or treating the current-constituent screen as live evidence
owner_session: /root
active_baseline:
  location: research/run_backtests.py
  code_identity: fcb441f754daa9ff83843187d763c748f7fa9040
  frozen_command: .venv/bin/python research/run_backtests.py
  required_tests:
    - preserves next-open execution, explicit costs, and existing app/data/backtest.json output
candidate:
  location: qforge
  allowed_files:
    - qforge/**
    - configs/**
    - tests/**
    - pyproject.toml
    - research/README.md
    - app/data/factor_backtest.json
    - app/page.tsx
    - app/globals.css
  scientific_choice_axis: configurable daily cross-sectional factor definition
admission:
  structure_command: python /Users/cailingling/.codex/skills/research-code-evolution-guard/scripts/structure_gate.py . --package qforge --json-out research/evidence/QF-FACTOR-ENGINE-01/structure_report.json
  semantic_commands:
    - .venv/bin/python -m pytest -q
    - .venv/bin/qforge demo --output research/demo
    - .venv/bin/qforge run --config configs/price_factors.yaml
    - .venv/bin/python research/run_backtests.py
  prior_behavior_map:
    - existing strategy runner retained unchanged and rerun after candidate admission
  permissions:
    local_checks: authorized by user request
    remote_execution: not required
    artifact_download: no weights or checkpoints
cutover:
  criteria:
    - structure gate passes
    - semantic tests pass
    - real-data factor report is generated
    - frozen baseline still passes
  rollback_target: fcb441f754daa9ff83843187d763c748f7fa9040
artifact_policy:
  allow: [source, configs, logs, metrics, reports, small demo data]
  deny: [weights, checkpoints, optimizer_state, large_model_cache]
status: candidate
```

## Local quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test,data]'

# Zero-network deterministic smoke test
.venv/bin/qforge demo

# Real local CSI800 factor run
.venv/bin/qforge run --config configs/price_factors.json

# Regression and future-data tests
.venv/bin/python -m pytest -q
```

The real run writes a complete research payload, a standalone HTML report and a
flat ranking CSV under `research/output/factor_engine/`. The website receives a
small derived payload at `app/data/factor_backtest.json`.

## Engine boundaries

- `qforge/data.py`: validates a long OHLCV table and creates aligned panels.
- `qforge/factors.py`: pure, registry-based signal functions. Ten OHLCV factors
  are currently executable; the 324-factor literature catalogue is not claimed
  to be executable without point-in-time accounting, event and analyst data.
- `qforge/preprocess.py`: lagged liquidity eligibility, MAD winsorisation,
  cross-sectional standardisation and factor composition.
- `qforge/analytics.py`: daily Spearman IC, ICIR, quantile curves and metrics.
- `qforge/portfolio.py`: next-open long-only simulation, weight drift, costs,
  market-regime filter and approximate one-price limit locks.
- `qforge/pipeline.py`: one reproducible experiment transaction.
- `qforge/reporting.py`: JSON, CSV and standalone local HTML outputs.

Input data must contain `date, symbol, open, high, low, close, volume`. To add a
factor, implement a pure `MarketPanel -> DataFrame` function and register one
`FactorSpec` in `qforge/factors.py`; all diagnostics and reports then run without
adding another experiment script.

## AH-01 baseline

- Evaluation window: 2025-08-25 through 2026-08-24.
- Design/diagnostic split ends 2026-02-24; the second half is shown separately.
- Universe: current CSI 300 and CSI 500 constituents downloaded from the official CSI files. This is a deliberate cheap first screen and is **not** survivorship-safe.
- Market data: adjusted daily OHLCV from Yahoo Finance; membership from China Securities Index.
- Signal: previous close and older data only; rebalance at the next adjusted open.
- Cost proxy: 15 bps on buys and 20 bps on sells, including a conservative slippage allowance. It does not yet model limit-up/limit-down non-fills or minimum broker commissions.
- Strategy family: long-only price momentum, risk-adjusted momentum, breakout and reversal-within-trend; top 3/5/10, equal/inverse-volatility weights, weekly/biweekly/monthly rebalance, optional 120/200-day market regime filter.
- Forbidden inference: a profitable curve is not evidence that the same return was achievable live. The current-constituent bias gate fails by construction.

Run in order:

```bash
.venv/bin/python research/build_factor_catalog.py
.venv/bin/python research/fetch_market_data.py
.venv/bin/python research/run_backtests.py
```
