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
  location: qforge
  code_identity: 53f382a5657f6cefd7de1889f6cd3d1b294b5816
  frozen_command: .venv/bin/qforge run --config configs/price_factors.json
  required_tests:
    - .venv/bin/python -m pytest -q
    - .venv/bin/qforge demo
    - .venv/bin/qforge run --config configs/price_factors.json
retained_baseline:
  location: research/run_backtests.py
  code_identity: fcb441f754daa9ff83843187d763c748f7fa9040
  frozen_command: .venv/bin/python research/run_backtests.py
  continuity: rerun passed after factor-engine admission
candidate:
  location: qforge
  state: active
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
  results:
    structure: pass, 0 findings, 952 package lines
    semantics: 7 passed
    demo: end-to-end JSON CSV HTML generated
    real_data: 11 factor and composite candidates evaluated on 800 symbols
    retained_baseline: 1116 strategy search rerun passed
cutover:
  criteria:
    - structure gate passes
    - semantic tests pass
    - real-data factor report is generated
    - frozen baseline still passes
  rollback_target: fcb441f754daa9ff83843187d763c748f7fa9040
  promoted_entrypoint: qforge.cli:main
artifact_policy:
  allow: [source, configs, logs, metrics, reports, small demo data]
  deny: [weights, checkpoints, optimizer_state, large_model_cache]
status: active
successor_goal:
  goal_id: QF-MINUTE-PAPER-01
  decision: Add a BaoStock 5-minute local database and next-bar A-share paper-trading engine while preserving the admitted daily engine.
  non_goals:
    - connecting a live broker account or transmitting real orders
    - claiming tick-level or order-book execution from 5-minute bars
    - scaling to the full A-share market before a small fixed-universe pilot passes
  owner_session: /root
  verified_active_baseline:
    location: qforge daily factor engine and local site
    code_identity: f710badb1e32d2acac576a8fda981bb67f6dc08f
    frozen_commands:
      - .venv/bin/python -m pytest -q
      - .venv/bin/qforge run --config configs/price_factors.json
      - npm run build
  candidate:
    location: qforge/minute
    allowed_files:
      - qforge/minute/**
      - qforge/cli.py
      - qforge/__init__.py
      - configs/minute_5m.json
      - tests/test_minute_*.py
      - pyproject.toml
      - research/README.md
      - research/evidence/QF-MINUTE-PAPER-01/**
      - app/data/minute_system.json
      - app/page.tsx
      - app/globals.css
    scientific_choice_axis: completed 5-minute cross-sectional close-strength signal executed at the next bar under A-share paper-trading constraints
  admission:
    structure_command: .venv/bin/python /Users/cailingling/.codex/skills/research-code-evolution-guard/scripts/structure_gate.py . --package qforge --json-out research/evidence/QF-MINUTE-PAPER-01/structure_report.json
    semantic_commands:
      - .venv/bin/python -m pytest -q
      - .venv/bin/qforge minute init --config configs/minute_5m.json
      - .venv/bin/qforge minute download --config configs/minute_5m.json
      - .venv/bin/qforge minute backtest --config configs/minute_5m.json
      - .venv/bin/qforge run --config configs/price_factors.json
      - npm run build
    prior_behavior_map:
      - existing seven daily-engine tests retained unchanged
      - daily factor CLI and local website build rerun before cutover
    permissions:
      local_checks: authorized by user request
      external_data_download: BaoStock anonymous historical data authorized by user request
      live_order_routing: forbidden without a separate explicit authorization and broker account scope
  cutover:
    criteria:
      - local schema and idempotent upsert tests pass
      - T+1, board-lot, minimum-commission and participation-limit tests pass
      - real BaoStock 5-minute pilot is stored and replayed with recoverable evidence
      - daily baseline and local website remain runnable
    rollback_target: f710badb1e32d2acac576a8fda981bb67f6dc08f
  artifact_policy:
    allow: [source, configs, database schema, logs, metrics, reports, small manifests]
    deny: [credentials, broker tokens, live orders, large raw database commits]
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
