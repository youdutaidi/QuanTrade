# QF-WALKFORWARD-01 — P2 input/accounting preparation

Date: 2026-08-26. Owner: `/root`. Rollback baseline: `be0c9f4`.
Frozen config remains P1 SHA256
`f946362d7d5e71e2e023e5412cd3024bada5edcec5eddd1b18737eaf2afdeae4`.

## Verdict

**Supported for synthetic accounting and input-admission semantics only.**
The real market experiment remains pending. No strategy return, cash/share
source completeness, investor-specific dividend taxation or verified strategy
is established by this gate.

QF-DATA-EXPANSION-01 remains the active empirical experiment; its single A5
source process was not interrupted or accompanied by another source session.
At 2026-08-26T05:15:02Z the inventory held 5,448,119 daily bars and 18,616
adjustment-factor records; 4,101 / 5,430 tasks succeeded. One retryable receive
failure remained. These are inventory counts, not final data admission.

## Evidence actually executed

- Full retained suite: **115 passed** (`tests.log`).
- Structure gate: **pass, zero findings** (`structure_report.json`).
- Maximum function/class/module/script spans: **40 / 249 / 325 / 31** lines,
  measured across `qforge` and `research/data_workflows` (`size_metrics.json`).
- 4,709 package lines and 89 workflow-script lines; script/package ratio 0.0189.
- No reported private imports or duplicate 20-line scaffolds. Role inspection:
  `execution.py` makes pure fill decisions; `ledger.py` alone owns the paper
  account; `ledger_audit.py` is a read-only witness; `demo.py` composes them and
  persistence. No account import of its witness and no cross-script imports.
- Existing daily, minute, validation, source and export tests remain included.
  Local HTTP smoke returned **200**. Verified registry remains **0**.

Executed commands:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python /Users/cailingling/.codex/skills/research-code-evolution-guard/scripts/structure_gate.py . --package qforge --scripts research/data_workflows --json-out research/evidence/QF-WALKFORWARD-01/P2/structure_report.json
.venv/bin/qforge walkforward ledger-demo --config configs/walk_forward.json --output research/evidence/QF-WALKFORWARD-01/P2/demo-A1
.venv/bin/qforge walkforward preflight --config configs/walk_forward.json --plan research/evidence/QF-WALKFORWARD-01/P1/frozen_plan.json
```

The real-input preflight exited **2**, as expected: no completed data manifest
exists yet. It did not load market outcomes. Synthetic tests separately reject
incomplete/mismatched manifests, absent source replay, altered configuration or
panel fingerprints, and panel replacement during loading. Development loading
uses a Parquet date predicate ending 2025-08-24; holdout rows are not loaded.

## Hand-accounting witness and persistence

`demo-A1` contains 12 events over three synthetic sessions: a buy, a cash/bonus
share entitlement, delayed settlement and a sell. Initial cash is CNY 1,000,000.
The hand-calculated closing equities are 999,984.90, 999,945.90 and 1,000,023.86.
These are invented fixture prices and amounts, not market or strategy results.

The independent witness imports neither the account nor its fill/fee functions.
It recomputes costs, available shares, receivables, cash and marked equity;
tampered fee, quantity, ownership, payment, sequence and equity tests fail.
Unavailable T+0 shares do not become sellable; bonus shares wait for listing;
payment-date dividends become cash only at the close. Missing close marks are
carried and flagged, not zeroed. Unknown reference-price resets or fractional
share allocation prevent a completed ledger.

The generated ledger was persisted and read back from
`research/data/qforge_walkforward.sqlite`, then replayed again:

- Run: `study-2d5beb2d5fd14894aa6ad7f631bddb72`.
- Event SHA256: `b09dcba56475328ec7a9b8b7c0c824e0d50d449536beb4a1ba3daacf65329ed3`.
- `kind=synthetic`, `verified_strategy=0`, all three sessions closed.
- Existing runs are not overwritten. A separate synthetic test detects a
  modified SQLite event and verifies that another run remains unchanged.

## Admission and remaining work

Reusable accounting behavior and CLI `walkforward ledger-demo` are admitted
only for their demonstrated scope. The `preflight` command fails closed.
`load_development_frame` remains a candidate for integration with the future
market runner; it has not been used to compute a real candidate return.
No live orders or broker integration were added.

Company-action inputs still need source-backed net-cash/tax and integer-share
allocation evidence. The witness cannot independently prove source prices,
opening liquidity, correct strategy signals or historical tax treatment merely
by agreeing with a ledger. Those remain distinct gates.

The user's added remote-delivery requirement was recorded in the canonical
contract. `origin` now points to the requested empty private QuanTrade repo;
SSH and ADMIN permission were checked. Nothing has been pushed yet. A root
README documents local use and makes these incomplete boundaries explicit.

Next discriminator: complete/admit the real daily panel, then test company-action
source coverage and a small ledger replay before the frozen market sweep.
