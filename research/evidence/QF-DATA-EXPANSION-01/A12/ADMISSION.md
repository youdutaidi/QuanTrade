# A12 candidate admission — raw archive audit

Evidence verdict: structure-admitted and semantics-admitted. The first focused
attempt passed all 15 new cases; the full retained suite passed all 186 tests
in 6.31 seconds. All 171 prior tests remain unchanged. Commands and outputs are
in `candidate-tests-A1.log`, `admission-tests.log`, and `structure-A1.json`.

The adversarial fixtures demonstrate that deleted planned work cannot masquerade
as completion, raw/count/ownership/provenance/projection defects fail closed,
and a concurrent WAL writer does not contaminate an already-open audit snapshot.
Successful empty years remain distinct from missing or failed requests. Audit
reports refuse overwrite. Legacy projections are explicitly not certified or
consumed; the checked raw source is re-normalized and old bytes remain unchanged.

Maintainability: one 198-line read-only witness owns diagnostic aggregation,
and the existing CLI composes lifecycle planning, daily-input admission and this
witness. `ActionStore` remains the sole archive writer. No source downloader,
normalizer, session lock, task planner, scientific state machine or strategy was
changed. There is no new runner script, duplicated workflow or unused export.
The public witness is consumed by the CLI and tests.

Measured maximums: function 40 lines, class 249, module 325, workflow script 31.
The structure checker reports zero layer, private-import or duplicate-scaffold
findings; package 6291 lines, script 89 lines, ratio 0.0141. `size-metrics.json`
records exact locations. Semantic scope is archival consistency, not independent
market data, tax correctness, cash/share economics or investable profitability.

Owner `/root`; candidate public command `qforge actions audit`; rollback target
`6c28760`. The next admitted discriminator is a read-only audit of the actual
in-progress database, with a new immutable report and measured runtime. A11's
already-loaded capture process and D3's frozen upload bytes stay unchanged.
