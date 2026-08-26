# Q-Forge research contract

## Final delivery requested by the user

- Destination: `git@github.com:youdutaidi/QuanTrade.git` (requested 2026-08-26).
- Delivery documentation may add the root `README.md`; the canonical experiment
  and evolution record remains this file, not a second status tracker.
- Deliver the complete local source, recoverable raw/derived data, configurations,
  test evidence and backtest artifacts, with hashes and restore instructions.
- Keep the local databases. Do not upload credentials, virtual environments,
  dependency caches or transient WAL files. SQLite data must be captured with a
  consistent backup/export, not by copying a changing database file alone.
- Inspect and preserve remote history; no force push or replacement of unrelated
  remote files. Code uses normal Git; database bundles may use the same repo's
  Releases because regular Git rejects individual files over 100 MiB.
- The first in-progress snapshot has passed remote download/restore verification
  and is published at `https://github.com/youdutaidi/QuanTrade/releases/tag/data-20260826-d2`.
  The later full-dataset delivery and strategy validation remain pending; this
  recovery milestone does not complete the research objective.
- Read-only remote check on 2026-08-26: repository is private, empty and the
  current account has ADMIN permission; SSH access succeeds. Local `origin`
  points to the requested repository. The first normal Git push of `main`
  succeeded at `21c816f89c7c42a2192bc6799452c985aa8cd003`; the remote
  `refs/heads/main` was read back and matches exactly.
- Delivery preparation D1 (non-empirical infrastructure, baseline `21c816f`):
  add bounded local snapshot, integrity verification and non-overwriting restore
  utilities. Allowed files: `qforge/delivery/**`, `qforge/cli.py`,
  `tests/test_delivery_*.py`, root `README.md`, this canonical record, and
  `research/evidence/DELIVERY-01/**`; generated bundles stay under the ignored
  `research/output/delivery/` tree or another explicitly excluded destination.
  The fixed source allowlist is `research/data`, `research/source`,
  `research/output` excluding `delivery`, `research/demo`, and `research/evidence`.
  Capture SQLite via online backup, not a bare live-file copy; exclude transient
  WAL/SHM, lock files, credentials and dependency caches. Preserve all source data.
- D1 cheapest falsifier: retain committed WAL rows, detect a changed byte,
  reject archive path traversal and refuse overwrite of a nonempty restore target.
  Run all retained tests and the structure gate before a real archive attempt.
  First release will be explicitly an in-progress snapshot, not completed data
  or a verified strategy. It must be downloaded and restored into a new directory
  before publication. No second source session or strategy parameter change.
- D1 preparation is structure- and semantics-admitted: 154 retained/new tests
  passed, including inner-member corruption with an updated outer hash; zero
  structural findings. A dirty code/config/test tree refused capture with exit 2.
  Evidence: `research/evidence/DELIVERY-01/D1/`. Real capture and remote asset
  round-trip remain pending; no remote data asset is claimed yet.
- D1 real-capture verdict: protocol-invalid for remote delivery. Its local-only
  manifest included `research/data/yf_cache/cookies.db`, a provider session
  cache. No Release or data upload was created. The generated archive is
  quarantined, while original data is preserved.
- D2 correction (same delivery task; baseline `27d9fe7`, same write surface):
  explicitly exclude the Yahoo provider cache and credential/cookie filenames
  during capture and reject them during archive verification/restoration.
  Add regression fixtures, rerun retained tests/structure, then capture a new
  `research/output/delivery/data-20260826-d2` artifact. Do not reuse D1 bytes.
- D2 preparation admitted: 156 tests pass, zero structure findings; the real
  quarantined D1 archive now fails verification before extraction because its
  manifest contains the excluded session cache. The new source-selection report
  explicitly excludes that cache and SQLite sidecars.
- D2 real upload succeeded: source commit `5368a6fe77aacec86e23a831338d82bd5b2a3ad5`
  was pushed and its remote SHA verified. Draft release `data-20260826-d2`
  contains the 636315381-byte archive and five supporting files. GitHub's archive
  SHA256 matches `0799eda5a445a1228f63168a304355e64ae821b84799e5099d15ddc55f34c94f`.
  Its 121-file snapshot includes 6065746 daily bars, 116160 five-minute bars,
  and the synthetic-ledger database; no provider Cookie cache is included.
  The two JSON manifests were downloaded and byte-compared successfully.
  The full archive is still downloading to `research/output/delivery/roundtrip-20260826-d2/`;
  do not publish before restoring it into a fresh directory and matching all
  hashes and SQLite inventories. Original A5 ingestion continues independently.
- D2 subsequent closure: all six downloaded source/support assets matched;
  121 members and all three SQLite inventories restored successfully into a new
  directory. Two proof assets were added and all eight remote asset hashes checked.
  Published 2026-08-26T06:28:50Z as a prerelease, not Latest; remote tag resolves
  to the exact frozen source commit. Evidence: `research/evidence/DELIVERY-01/D2/`.

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
      - id: QF-DATA-EXPANSION-01-A8
        decision: make live inventory counts and integrity/coverage checks observe one SQLite read snapshot
        baseline: b6d7f5d
        counterexample: A7 live audit observed 3218 successful tasks in inventory and 3219 in coverage because ingestion advanced between separate read transactions
        cheapest_falsifier: commit a missing bar from a second WAL connection during the audit; all reported counts must remain on the initial snapshot
        write_surface: qforge/marketdata/store.py, qforge/marketdata/audit.py, tests/test_marketdata_coverage.py, research/README.md, research/evidence/QF-DATA-EXPANSION-01/A8/**
        state: structure-admitted and semantics-admitted; 63 tests passed; live audit now uses one read transaction; no change to source data or strategy parameters
      - id: QF-DATA-EXPANSION-01-A9
        decision: retain raw annual dividend responses, including queried-empty years, in a resumable local archive without interpreting source after-tax values as investor-specific cash
        baseline: 7a1fe0b
        scientific_choice_axis: unchanged market coverage and strategy specification; close the raw corporate-action provenance gap
        write_surface: qforge/actions/**, qforge/marketdata/provider.py, qforge/marketdata/session.py, qforge/minute/provider.py (session exclusion only), qforge/cli.py, configs/corporate_actions.json, tests/test_actions_*.py, tests/test_marketdata_provider.py, tests/test_marketdata_session.py, tests/test_minute_provider.py, research/README.md, research/evidence/QF-DATA-EXPANSION-01/A9/**
        source_contract: BaoStock query_dividend_data with yearType operate; request every overlapping lifecycle year for Shanghai and Shenzhen A shares, including delisted stocks; preserve schema, strings, nulls, response identity, errors, timestamps and hashes
        cheapest_falsifier: wrong or partial responses cannot complete a checkpoint; queried-empty responses must persist; interrupted requests resume without duplicate events; a second source session must fail before login
        input_gate: preview reads only security lifecycle; network ingestion requires the completed daily-panel manifest and no running daily-download record; A5 must finish before any new source session starts
        semantic_commands: retained pytest suite, structure gate, read-only real lifecycle plan, refusal check while A5 is active; no live corporate-action pilot before these pass
        outcomes: passing fixtures admits capture mechanics only; source gaps or ambiguous cash/share/tax fields remain unresolved; failed gates retain the old baseline and prevent a source launch
        state: structure-admitted and capture-semantics-admitted; 144 retained and new tests pass; zero structural findings; real action-source pilot pending daily completion
        real_preview: 5424 A-share symbols and 34476 overlapping lifecycle-year tasks; scope SHA256 5983b1dc73827d5cbe7da6787f5c05858e1e38e1fdbe00291ba29c6079cc5ad8
        source_refusal: real max-tasks 1 command exited 2 before database initialization or source login because A5 is active
        continuity: all prior 115 tests retained; minute database still has 116160 real bars; local HTTP 200; frozen strategy config unchanged
        evidence: research/evidence/QF-DATA-EXPANSION-01/A9
        claim_boundary: raw dividend capture is not full corporate-action coverage, rights-issue accounting, investor-specific taxation, or economic P&L validation
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
  preparation:
    state: configuration and synthetic-data implementation only; no market-outcome computation before data admission
    baseline: f1d17d1
    owner_session: /root
    allowed_files:
      - configs/walk_forward.json
      - qforge/walkforward/**
      - qforge/cli.py
      - tests/test_walkforward_*.py
      - research/README.md
      - research/evidence/QF-WALKFORWARD-01/**
    cheapest_falsifier: prefix-invariance, historical-rule boundary, fixed-grid cardinality and holdout-overlap tests
    retained_baseline: all existing daily, minute, validation and market-data tests; qforge minute status; local HTTP smoke
    structure_gate: qforge package with function 50, class 300 and module 400 line limits
    market_run_gate: completed market manifest and fingerprint must pass verify-panel; no live orders
    empirical_experiment: QF-DATA-EXPANSION-01 remains the sole active empirical experiment during preparation
    evidence: research/evidence/QF-WALKFORWARD-01/P1
    result: 92 retained and new tests pass; zero structure findings; minute database status and local HTTP 200 preserved
    frozen_config_sha256: f946362d7d5e71e2e023e5412cd3024bada5edcec5eddd1b18737eaf2afdeae4
    claim_boundary: preparation admitted only; no new market return, portfolio replay, corporate-action P&L or verified strategy
    next_preparation:
      id: QF-WALKFORWARD-01-P2
      baseline: be0c9f4
      decision: admit only fingerprint-matched completed inputs and make a replayable cash/share accounting state machine before market-outcome execution
      scientific_choice_axis: unchanged P1 factors, grid, fees, periods and selection; no new market data outcomes
      write_surface: qforge/walkforward/**, tests/test_walkforward_*.py, research/README.md, research/evidence/QF-WALKFORWARD-01/P2/**
      cheapest_falsifier: reject an incomplete or altered panel; reconcile a hand-calculated three-session ledger with first-day costs, T+1, delayed dividends and bonus shares
      scope: synthetic accounting and input admission only; corporate-action source coverage and investor-specific dividend taxation are not inferred from adjusted prices
      accounting_conventions: cash dividends remain receivables until payment-session close; bonus shares are valued from ex-date but cannot trade before listing; unknown fractional allocations and unresolved reference-price changes fail closed
      outcomes: matching hand ledger supports accounting semantics only; mismatch refutes implementation; incomplete input blocks market execution; all old tests must remain passing
      state: synthetic accounting and input-admission semantics admitted; market integration pending
      results: 115 retained and new tests pass; zero structural findings; synthetic ledger persisted to SQLite and independently reloaded/replayed; real input preflight exits 2 until final data manifest exists
      evidence: research/evidence/QF-WALKFORWARD-01/P2
    execution_preparation:
      id: QF-WALKFORWARD-01-P3
      baseline: e299f48
      owner_session: /root
      decision: connect the frozen causal scores to scheduled portfolio intents, dated opening fills and the existing cash/share account before the admitted real-data sweep
      write_surface: qforge/walkforward/**, tests/test_walkforward_*.py, research/README.md, research/evidence/QF-WALKFORWARD-01/P3/**; append explicitly synthetic runs to research/data/qforge_walkforward.sqlite only after admission
      scientific_choice_axis: unchanged P1 families, 144 candidates, development/holdout dates and execution costs; no market outcomes read during preparation
      input_contract: explicit trading calendar and historical security lifecycles; adjusted-price signals, raw execution prices; missing listed bars or held delisting without settlement evidence fail closed
      sizing_convention: rank at preceding completed close; budget from preceding account equity; quantity from current pre-opening reference price, never current raw open or close; account economic shares include pending bonus shares
      ordering_convention: first evaluation session and each rebalance interval thereafter; sells in symbol order then buys in frozen signal rank order; unfilled remainder canceled until a new scheduled signal
      lag_convention: execution volume_lag is measured from execution date, so lag 1 ends at preceding completed session; signal liquidity retains its existing t-minus-1 lag
      concentration_convention: 10 percent is the submitted target-slot cap, not a guarantee against subsequent mark-to-market drift; realized concentration is reported
      accounting_continuity: remove settled zero-share positions only at the following session open, with matching independent replay; earlier snapshots remain unchanged and pending-share claims are retained
      reporting_convention: returns include initial entry costs and start from initial cash; actual-calendar CAGR uses the declared inclusive window and is omitted for windows shorter than one year; risk metrics use daily closing equity, not intraday extrema
      cheapest_falsifier: change future prices or execution-day volume without changing earlier decisions; hand-check target quantities, fees, canceled orders, delayed distributions and first-day equity
      admission_commands: retained pytest suite, structure gate, full frozen-grid synthetic execution smoke, persisted ledger reload and independent arithmetic replay
      retained_baseline: all 156 existing tests, unchanged frozen strategy-config fingerprint, unchanged minute data and local website
      state: execution-mechanics admitted; 168 retained/new tests pass and structure has zero findings; real-data workflow remains gated on daily completion and verified corporate-action inputs
      formal_synthetic_attempt: synthetic-grid-A2 ran all 144 frozen candidates across 16 score settings; 7344 events persisted and independently reloaded/replayed; all short-window CAGR values deliberately omitted
      evidence: research/evidence/QF-WALKFORWARD-01/P3
      outcomes: semantic mismatch stops cutover; source or settlement gaps retain incomplete evidence without a return ranking; passing synthetic tests admits execution mechanics only
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
  exact_pre_outcome_specification:
    canonical_config: configs/walk_forward.json
    market_residual: lagged 60-session OLS intercept and beta against CSI300 price-index returns; no Fama-French replication claim
    composite_windows: short uses momentum 60 skip 5, reversal 5, IVOL 20, MAX 20; medium uses 120 skip 21, 10, 60, 20; long uses 252 skip 21, 20, 60, 60
    standardization: clip each cross-section to median plus or minus 5 raw MAD, then sample-standardize; zero MAD skips clipping; missing components excluded
    liquidity: median raw amount over 20 completed sessions ending t-1 at least CNY 20000000
    capital: CNY 1000000; unfilled stock slots remain cash; targets are 1 over requested top_n
    brokerage: all-in commission 0.0003, minimum CNY 5 per filled order; includes handling and regulatory fees, excludes stamp and transfer
    stamp_duty: seller 0.001 before 2023-08-28, 0.0005 thereafter
    transfer_fee: both sides 0.00002 before 2022-04-29, 0.00001 thereafter
    slippage: 10 basis points adverse to each side, rounded adversely to CNY 0.01
    execution_capacity: at most 0.5 percent of lagged 20-session median raw share volume; this is a daily-data capacity proxy, not opening-auction queue proof
    order_policy: next session only, sells before buys, cancel any unfilled quantity; no hidden retries; no same-day resale of new shares
    limit_policy: conservative reject at the adverse opening limit or if modeled slippage exceeds that limit; reject unexplained out-of-band opens
    corporate_actions: adjusted-price signals permitted; economic P&L cannot be certified without a separate cash and share event ledger
    multiple_testing: stationary bootstrap with expected block 20 sessions, 2000 replications, seed 20260826; one-sided family-wise alpha 0.05
    tie_break: descending score then ascending BaoStock symbol; selection ties resolve by candidate ID
  search_control:
    - the 144-candidate grid above is immutable before the first outcome is computed
    - candidate selection uses only discovery and the three walk-forward folds
    - the three folds are development/selection evidence, not unbiased out-of-sample evidence for the winner; only the untouched final holdout may support that claim
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

## Frozen successor preparation

`qforge walkforward plan --config configs/walk_forward.json` validates the
144-candidate specification without reading market outcomes. The optional
`--output PATH` writes a new, non-overwritable plan with its configuration
fingerprint. Preparation implements 16 distinct signal settings expanded across
nine portfolio schedules; it does not claim 144 independently discovered factors.
The existing daily and minute engines are preserved. Portfolio replay and
corporate-action cash/share verification remain separate admission gates.

```bash
# Refuses incomplete data and checks the original pre-outcome configuration.
.venv/bin/qforge walkforward preflight --config configs/walk_forward.json \
  --plan research/evidence/QF-WALKFORWARD-01/P1/frozen_plan.json

# Synthetic accounting only. Use a new output directory for every attempt.
.venv/bin/qforge walkforward ledger-demo --config configs/walk_forward.json \
  --output research/output/ledger-demo-local
```

The ledger demo writes append-only runs and events to
`research/data/qforge_walkforward.sqlite`. Cash dividends are separate from
spendable cash until settlement; bonus shares remain unavailable until their
listing date. Supplied net cash/tax and allocation evidence are explicit inputs,
not inferred from the adjusted-price feature chain. Independent arithmetic
replay does not independently validate the source prices or investor-specific
tax treatment. No live order is sent.

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
  universe observations, and explicit exact/boundary-exclusion reconstruction audits.
- Market layer: unadjusted daily OHLCV, exchange pre-close and percentage
  change, trading status, ST flag, turnover, amount, and adjustment factors.
- Research export: an adjusted-price OHLC feature chain uses BaoStock's
  exchange-adjusted `preclose`/`pctChg` fields so ex-dates do not create false
  price crashes; raw prices, amount and trading-state fields remain available.
  This is not an economic total-return ledger: cash dividends, share changes,
  rights and taxes require separate verification before any P&L claim.
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
