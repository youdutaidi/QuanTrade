# P3 — causal scores to a scheduled cash/share account

Verdict: **execution mechanics supported; real-market strategy validation pending**.
Owner `/root`; baseline/rollback `e299f48`. The 144-candidate specification remains
SHA256 `f946362d7d5e71e2e023e5412cd3024bada5edcec5eddd1b18737eaf2afdeae4`.

## Scope actually admitted

- Pure alignment of explicit sessions and stock lifecycles; no current-survivor
  filter. Missing listed bars, unknown status, out-of-lifecycle bars and incomplete
  benchmark closes refuse rather than fill silently.
- Sixteen reusable causal score settings feed the unchanged 144 schedule/size
  combinations. Order targets use the preceding completed signal and account
  equity plus a pre-opening reference price, not the subsequently observed open.
- Execution capacity ends at the preceding session for `volume_lag=1`; signal
  liquidity keeps the original separate t-minus-1 lag. Sells precede buys;
  unfilled quantity is not retried before a new scheduled signal.
- The existing account owns all money/shares. Pending bonus shares count toward
  economic exposure without becoming tradable early. Settled zero positions are
  removed only on the following session; pending shares are retained.
- Held delisting without settlement evidence fails; unresolved opening reference
  prices now fail before any opening orders. Failure objects retain the ledger
  prefix and any intents actually created, without supplying a performance result.
- Metrics include the initial funding point/entry costs and the declared calendar
  window. Shorter-than-year samples omit CAGR. Concentration is reported as observed
  mark-to-market weight; the 10% rule is a target-slot cap, not continuous drift control.

## Checks actually run

- First targeted run: 9 passed, 1 failed; opening reference checks were too late
  across symbols (`A1.md`). The correction preserved all old account guards.
- Final retained/new suite: **168 passed in 6.58 s** (`admission-tests-final.log`).
  All 156 pre-P3 tests remain. Tests cover future-price prefix invariance, no
  opening-price order sizing, no execution-day volume capacity, hand-computed
  first-day equity/costs, pending shares, cancellation schedules, missing actions,
  held delisting, and independent replay after pruning zero positions.
- Structure: **zero findings**, 6,057 package lines / 89 workflow lines, ratio
  0.0147 (`admission-structure.json`). Max function 40, class 249, module 325,
  workflow script 31 (`size_metrics.json`); no reported layer/private-import/
  duplicated-scaffold violation.
- Actual command:

```bash
.venv/bin/qforge walkforward execution-demo --config configs/walk_forward.json \
  --output research/evidence/QF-WALKFORWARD-01/P3/synthetic-grid-A2 --all-candidates
```

It used **1,680 generated rows**, not BaoStock bars: 144 candidate runs, 16 score
settings, 7,344 SQLite ledger events. Each run was read back and independently
arithmetically replayed; every session closed and every audit passed. All reported
annualized returns are null because the synthetic evaluation window is short.
The shared study database now additionally contains these explicitly synthetic
runs; its schema still forbids `verified_strategy=1`.
- Local website HTTP smoke returned 200. No old daily/minute runner or old
  semantic test was removed. No real market outcomes or holdout were loaded.

## Public surfaces and remaining work

Reusable interfaces: `prepare_replay_inputs`, `build_score_cache`,
`plan_rebalance`, `replay_candidate`; synthetic integration command
`qforge walkforward execution-demo`. `PaperAccount` remains the single balance
owner. The workflow composes the independent witness; the execution/math modules
do not import it. No broker or network action occurs in this preparation.

Not admitted: economic corporate-action source coverage, shareholder-specific
tax/fractional allocation, exceptional sessions, delisting settlement, actual
auction queue fills, real-market compute cost, full development selection,
multiple-testing correction, holdout or forward paper performance. The original
data experiment remains the only active empirical experiment. Next: complete its
current audit/source-replay/export gate and validate the raw dividend pilot before
connecting real data to this reusable executor.
