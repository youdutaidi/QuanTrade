# P4 workflow admission

All 190 retained/new tests pass in 6.49 seconds, preserving all 186 baseline
tests unchanged. Four additive tests cover full frozen-setting preparation
without portfolio/database creation, immutable output, missing-bar early stop,
ineligible finite scores, and exclusion of holdout calendar dates. Existing
Parquet predicate-pushdown and replacement/tampering tests remain passing.

Structure: zero findings; 6381 package lines, 89 workflow-script lines, ratio
0.0139. The existing pure signal/alignment implementations are unchanged.
`inputs.py` owns the small read-only reference adapter; `feature_check.py` is a
workflow composing admitted inputs and pure calculations and writing a compact
result. No new source session, execution state machine, selection axis or script
was introduced. Both public additions are consumed by the CLI/workflow and tests.

The new command may run against the entire real development panel under its
frozen fingerprint and configuration. This is **not** economic replay or a
strategy sweep: no orders, cash flows, winner selection, returns, significance
statistics, holdout performance or verified-strategy promotion are permitted.
Capture the real command log, timing/RSS and any first input failure unchanged.

Owner `/root`; command `qforge walkforward feature-check`; rollback `64f3bbf`.
Cost, full real alignment and all-setting coverage remain unverified until the
actual attempt. Company-action and economic-execution gates remain separate.
