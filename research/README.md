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
    state: active
    admitted_code_identity: e01960de2e0d7c9235482579f97b921678a76c8a
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
    results:
      structure: pass, 0 findings, 1968 package lines
      semantics: 13 passed including retained daily tests
      data: 116160 real BaoStock 5-minute bars, 10 symbols, 242 trading days
      paper_replay: succeeded with 1125 orders and 1124 fills
      scientific_verdict: close-strength candidate falsified at -36.96 percent net return and -46.46 percent max drawdown
      continuity: daily factor engine and local site build passed
  cutover:
    criteria:
      - local schema and idempotent upsert tests pass
      - T+1, board-lot, minimum-commission and participation-limit tests pass
      - real BaoStock 5-minute pilot is stored and replayed with recoverable evidence
      - daily baseline and local website remain runnable
    rollback_target: f710badb1e32d2acac576a8fda981bb67f6dc08f
    promoted_entrypoints:
      - qforge minute init
      - qforge minute download
      - qforge minute backtest
      - qforge minute status
  artifact_policy:
    allow: [source, configs, database schema, logs, metrics, reports, small manifests]
    deny: [credentials, broker tokens, live orders, large raw database commits]
  status: active
next_goal:
  goal_id: QF-VALIDATION-GATE-01
  decision: Replace performance-first website claims with a machine-enforced strategy admission registry; no strategy may be presented as verified unless every frozen evidence gate passes.
  non_goals:
    - guaranteeing or fabricating a 100 percent annualized return
    - changing strategy definitions or searching parameters inside this experiment
    - routing live orders or connecting a broker
  owner_session: /root
  verified_active_baseline:
    location: qforge daily engine, qforge/minute paper engine, and local site
    code_identity: 1485bffcdcd7fa3e1d254d9d301a16140251c36d
    frozen_commands:
      - .venv/bin/python -m pytest -q
      - .venv/bin/qforge minute status --config configs/minute_5m.json
      - npm run build
  candidate:
    location: qforge/validation.py and app validation surfaces
    state: candidate
    allowed_files:
      - qforge/validation.py
      - tests/test_validation.py
      - configs/validation_policy.json
      - research/validation_workflows/**
      - research/README.md
      - research/evidence/QF-VALIDATION-GATE-01/**
      - app/data/validation_registry.json
      - app/page.tsx
      - app/globals.css
    scientific_choice_axis: immutable strategy evidence-admission policy
  admission:
    structure_command: .venv/bin/python /Users/cailingling/.codex/skills/research-code-evolution-guard/scripts/structure_gate.py . --package qforge --scripts research/validation_workflows --json-out research/evidence/QF-VALIDATION-GATE-01/structure_report.json
    semantic_commands:
      - .venv/bin/python -m pytest -q
      - .venv/bin/python research/validation_workflows/build_registry.py
      - npm run build
    prior_behavior_map:
      - all existing daily and minute engine tests retained unchanged
      - existing local launch command retained
      - rejected strategies remain recoverable as research evidence but are removed from the verified registry
    permissions:
      local_checks: authorized by user request
      external_data_download: deferred to successor data experiment
      live_order_routing: forbidden without separate explicit authorization
    results:
      structure: pass, 0 findings, 2062 package lines
      semantics: 17 passed including retained daily and minute tests
      registry: 3 assessed, 0 verified, 3 rejected
      site: production build passed and local HTTP smoke returned 200
      scientific_verdict: performance-only evidence is insufficient; every existing candidate remains rejected
  cutover:
    criteria:
      - validation policy rejects both current daily high-return candidates and the failed minute candidate
      - website reports zero verified strategies until evidence actually passes
      - structure gate, retained tests, registry build, and site build pass
    rollback_target: 1485bffcdcd7fa3e1d254d9d301a16140251c36d
    bounded_exceptions:
      - legacy scripts research/build_factor_catalog.py, research/fetch_market_data.py, and research/run_backtests.py retain pre-existing size findings and are outside this goal's write surface; the candidate workflow has its own gated directory
  artifact_policy:
    allow: [source, configs, logs, metrics, reports, small manifests]
    deny: [credentials, broker tokens, live orders, large raw database commits]
  status: admitted
data_goal:
  goal_id: QF-DATA-EXPANSION-01
  decision: Build a resumable BaoStock-backed A-share research database with point-in-time universe membership, security lifecycle, corporate actions, and multi-year daily bars before any new strategy search.
  non_goals:
    - claiming the database or a discovery backtest is already a verified strategy
    - mixing Hong Kong data from a source without equivalent point-in-time provenance
    - transmitting live orders or storing broker credentials
  owner_session: /root
  verified_active_baseline:
    location: qforge daily engine, qforge/minute paper engine, validation registry, and local site
    code_identity: 8ed8c9e
    frozen_commands:
      - .venv/bin/python -m pytest -q
      - .venv/bin/qforge minute status --config configs/minute_5m.json
      - .venv/bin/python research/validation_workflows/build_registry.py
      - npm run build
  candidate:
    location: qforge/marketdata and research/data_workflows
    state: candidate
    allowed_files:
      - qforge/marketdata/**
      - qforge/cli.py
      - configs/market_data.json
      - tests/test_marketdata_*.py
      - research/data_workflows/**
      - research/README.md
      - research/evidence/QF-DATA-EXPANSION-01/**
      - app/data/data_inventory.json
      - app/page.tsx
      - app/globals.css
    scientific_choice_axis: point-in-time A-share data coverage; no strategy parameters change in this experiment
  admission:
    structure_command: .venv/bin/python /Users/cailingling/.codex/skills/research-code-evolution-guard/scripts/structure_gate.py . --package qforge --scripts research/data_workflows --json-out research/evidence/QF-DATA-EXPANSION-01/structure_report.json
    semantic_commands:
      - .venv/bin/python -m pytest -q
      - .venv/bin/qforge market init --config configs/market_data.json
      - .venv/bin/qforge market download-reference --config configs/market_data.json
      - .venv/bin/qforge market status --config configs/market_data.json
      - npm run build
    prior_behavior_map:
      - all validation, daily-engine, and minute-engine tests remain unchanged
      - verified strategy count remains zero after data ingestion
    permissions:
      local_checks: authorized by user request
      external_data_download: BaoStock anonymous historical data authorized by user request
      live_order_routing: forbidden without separate explicit authorization
    attempts:
      - id: QF-DATA-EXPANSION-01-A1
        change: four concurrent BaoStock sessions with atomic SQLite task claiming
        result: protocol-invalid after the provider session began failing repeatedly
        recovery: deleted only 339616 daily bars and 1203 adjustment factors; retained reference tables; reset all daily checkpoints
        evidence: research/evidence/QF-DATA-EXPANSION-01/concurrency_reset.log
      - id: QF-DATA-EXPANSION-01-A2
        change: one BaoStock session, refreshed every 200 securities with a two-second batch pause
        result: interrupted after 811 successes when one query call stopped responding before the full-call timeout patch was loaded
        evidence: research/evidence/QF-DATA-EXPANSION-01/daily_single_verified.log
      - id: QF-DATA-EXPANSION-01-A3
        change: bound the full query call and row stream to 90 seconds; discard and recreate a session after every request error
        result: recovered transient sessions and retained 2021911 bars; terminated after a repeated login failure
        evidence: research/evidence/QF-DATA-EXPANSION-01/daily_single_resume_2.log
      - id: QF-DATA-EXPANSION-01-A4
        change: increment attempt counters only when a request executes, retry login three times, and let the completion transaction recover failed download passes
        result: stopped for A5 integrity corrections at 2240 completed tasks and 2975440 daily bars; all market rows preserved
        evidence: research/evidence/QF-DATA-EXPANSION-01/complete_recovery.log
      - id: QF-DATA-EXPANSION-01-A5
        change: reject partial provider streams and wrong response identities; check successful tasks against the trading calendar; distinguish optional suspended delisting-date rows; label adjusted-price chains separately from economic total return
        state: experiment-admitted after 49 retained and new tests and zero structure findings; no strategy search or data deletion
        baseline: 40e329f
        cheapest_falsifier: synthetic partial-stream, missing-date, delisting-boundary, and extreme-loss regression tests
        admission: retained full test suite and structure gate before restarting the single source session
        evidence: research/evidence/QF-DATA-EXPANSION-01/A5
        pre_resume_verdict: all 2240 successful tasks have complete pre-delisting calendar coverage; 69 optional suspended boundary rows retained; no integrity violations; full data admission still pending
      - id: QF-DATA-EXPANSION-01-A6
        change: replay reference snapshots after the exclusive delisting-view migration; explicitly distinguish raw equality from audited nontradable boundary exclusions
        baseline: 77ce68f
        cheapest_falsifier: a tradable delisting-date observation must remain a mismatch; raw count differences and hashes must remain visible
        evidence: research/evidence/QF-DATA-EXPANSION-01/A6
        source_job: A5 continues under 77ce68f; A6 changes only reference comparison and presentation, not network downloads
        result: structure-admitted and semantics-admitted; 50 tests passed; 5 exact snapshots and 2 explicit pass_boundary snapshots; local build and HTTP 200 passed
        real_panel_smoke: 40 deterministic available symbols and 51906 rows transformed with finite tradable OHLC and prefix invariance; this is not a strategy backtest or corporate-action P&L validation
        next_action: let the A5 single downloader finish, then rerun complete under the A6 audit; do not start a second BaoStock session
      - id: QF-DATA-EXPANSION-01-A7
        decision: make final data admission compare both bars and adjustment factors and export a bounded-memory, atomic, fingerprinted research panel
        baseline: a7301e8
        write_surface: qforge/marketdata/**, tests/test_marketdata_*.py, research/README.md, research/evidence/QF-DATA-EXPANSION-01/A7/**, research/evidence/QF-DATA-EXPANSION-01/completion_runs/**, research/evidence/QF-DATA-EXPANSION-01/data_completion.json
        scientific_choice_axis: unchanged data coverage; no strategy or selection parameter changes
        cheapest_falsifier: corrupted factor values must fail replay; chunked export must equal the reference transform and preserve the previous artifact on failure
        state: structure-admitted and semantics-admitted; 62 tests pass; real-data export cost check passed; final source replay pending download completion
        source_job: no second source session; A5 downloader continues under its frozen code
        real_export_cost: 3709150 rows and 2823 symbols; 11.33 seconds; 533086208 peak resident bytes; candidate Parquet SHA256 d945ab19fcae58d2ef3f86ad40ab76269d7c5b3eea534c798e279e1d24c5d6cf
        evidence_extension: each final completion records immutable audit, source replay, panel fingerprint and result; latest pointer is atomic; export failures or mid-run code changes cannot emit ready
        admission_extension: complete civil-day calendar coverage is required; verify-panel refuses incomplete manifests, absent source samples and replaced artifacts
  cutover:
    criteria:
      - SQLite schema, idempotent upserts, checkpoint resume, and source normalization tests pass
      - historical trade calendar, full security lifecycle, and point-in-time universe samples persist locally
      - every download run and failure is recoverable from the database
      - retained baseline tests and local website build pass
    rollback_target: 8ed8c9e
  artifact_policy:
    allow: [source, configs, schema, logs, metrics, small manifests]
    deny: [credentials, broker tokens, live orders, committing the large local database]
  status: candidate
planned_strategy_goal:
  goal_id: QF-WALKFORWARD-01
  decision: Test a frozen A-share family combining residual momentum, short-term reversal, low idiosyncratic volatility, and lottery-stock avoidance on the completed point-in-time database.
  hypothesis: a low-turnover composite that avoids high-MAX and high-idiosyncratic-volatility stocks is more stable than conventional raw momentum in the retail-dominated A-share market.
  candidate_families:
    - residual momentum after rolling market-beta removal
    - 5-to-20-day reversal
    - 20-to-60-day low idiosyncratic volatility
    - 20-day low maximum daily return
    - equal-weight standardized composite of the four families
  frozen_parameter_grid:
    residual_momentum:
      lookback_days: [60, 120, 252]
      skip_days: [5, 21]
      rebalance_days: [5, 10, 20]
      top_n: [10, 20, 50]
      candidates: 54
    short_reversal:
      lookback_days: [5, 10, 20]
      rebalance_days: [5, 10, 20]
      top_n: [10, 20, 50]
      candidates: 27
    low_idiosyncratic_volatility:
      lookback_days: [20, 60]
      rebalance_days: [5, 10, 20]
      top_n: [10, 20, 50]
      candidates: 18
    low_maximum_return:
      lookback_days: [20, 60]
      rebalance_days: [5, 10, 20]
      top_n: [10, 20, 50]
      candidates: 18
    fixed_equal_composite:
      windows: [short, medium, long]
      rebalance_days: [5, 10, 20]
      top_n: [10, 20, 50]
      candidates: 27
    total_candidates: 144
  frozen_walk_forward:
    discovery: 2020-08-25 to 2022-08-24
    fold_1: train through 2022-08-24, test 2022-08-25 to 2023-08-24
    fold_2: train through 2023-08-24, test 2023-08-25 to 2024-08-24
    fold_3: train through 2024-08-24, test 2024-08-25 to 2025-08-24
    untouched_holdout: 2025-08-25 to 2026-08-24
  frozen_execution:
    signal_cutoff: completed close at t
    fill: next tradable open at t+1
    eligibility: listed at t, at least 120 trading days old, non-ST, tradable, lagged 20-day median amount floor
    portfolio: long-only, equal weight, no leverage, maximum 10 percent per stock
    frictions: board lots, minimum commission, stamp duty, transfer fee, slippage, price limits, and T+1
  search_control:
    - the 144-candidate grid above is immutable before the first outcome is computed
    - candidate selection uses only discovery and the three walk-forward folds
    - untouched holdout is opened once for the selected candidate
    - family-wise performance receives a stationary-bootstrap multiple-testing correction
    - selection maximizes median fold CAGR subject to every fold being positive and no fold drawdown breaching -35 percent
  admission:
    - validation policy 1.0 passes every conjunctive gate
    - annualized out-of-sample return is at least 100 percent
    - Sharpe is at least 1.5 and maximum drawdown is no worse than -35 percent
    - an independent order-ledger replay matches cash, positions, costs, and equity
  status: pending until QF-DATA-EXPANSION-01 is admitted
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

## Minute local system

The minute pipeline is local-only and never routes an order to a broker:

```bash
.venv/bin/qforge minute init --config configs/minute_5m.json
.venv/bin/qforge minute download --config configs/minute_5m.json
.venv/bin/qforge minute backtest --config configs/minute_5m.json
.venv/bin/qforge minute status --config configs/minute_5m.json
```

- Market database: `research/data/qforge_minute.sqlite` (ignored by Git).
- Source: BaoStock unadjusted 5-minute OHLCV, fixed ten-symbol pilot.
- Coverage: 116,160 bars from 2025-08-25 through 2026-08-24.
- Ledger: local signals, orders, fills, T+1 positions and equity snapshots.
- Execution: completed 14:50 bar signal, next 14:55 bar open, 100-share
  board lots, T+1, minimum commission, sell stamp duty, transfer fee, slippage
  and five-percent bar-volume participation.
- First scientific verdict: the daily close-strength rotation is falsified in
  this pilot (`-36.96%` total return, `-46.46%` maximum drawdown). The engine is
  admitted; the strategy is not promoted.

## Point-in-time A-share database

The multi-year daily database is local-only and uses resumable per-security
checkpoints. Run exactly one BaoStock download process at a time: the provider's
own download guidance warns that concurrent sessions can corrupt compressed
responses.

```bash
.venv/bin/qforge market init --config configs/market_data.json
.venv/bin/qforge market download-reference --config configs/market_data.json
.venv/bin/qforge market download-daily --config configs/market_data.json --recover
.venv/bin/qforge market status --config configs/market_data.json
.venv/bin/python research/data_workflows/audit_market_database.py \
  --config configs/market_data.json \
  --output research/evidence/QF-DATA-EXPANSION-01/data_audit.json
.venv/bin/python research/data_workflows/export_research_panel.py \
  --config configs/market_data.json \
  --output research/data/qforge_daily_panel.parquet
```

- Database: `research/data/qforge_market.sqlite` (ignored by Git).
- Reference layer: trade calendar, full security lifecycle, sampled historical
  universe observations, and zero-difference lifecycle reconstruction audits.
- Market layer: unadjusted daily OHLCV, exchange pre-close and percentage
  change, trading status, ST flag, turnover, amount, and adjustment factors.
- Research export: a synthetic total-return OHLC series uses BaoStock's
  exchange-adjusted `preclose`/`pctChg` fields so ex-dates do not create false
  price crashes; raw amount and trading-state fields remain available.
- Recovery: interrupted tasks return to `pending` with `--recover`; succeeded
  tasks are never fetched twice and all writes are idempotent.

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
