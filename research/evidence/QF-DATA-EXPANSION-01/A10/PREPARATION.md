# A10 — final daily admission and bounded raw-dividend pilot

Frozen implementation: `cc77d70`; daily scope and `configs/walk_forward.json`
unchanged. The retained suite has 168 passing tests and the P3 structure gate
has zero findings. No source changes are part of this attempt.

A5 completed 5430 tasks, including its failed-request retry. Its final audit
found no missing mandatory calendar rows and no integrity violations, but the
old running implementation rejected the two explicitly audited nontradable
delisting-boundary snapshots. The current audit already tests that distinction;
this attempt does not relax it further.

1. Run the existing `market complete` command once. Record immutable completion
   evidence and stop if audit, independent source replay or export fails.
2. Run `market verify-panel` against the emitted manifest and panel fingerprint.
3. Only after both pass, run the existing `actions download --max-tasks 1`.
   Inspect the raw schema, source/request identity, dates, nulls and normalization.
4. If valid, permit at most nine additional requests and inspect their evidence
   before considering the remainder of the already-frozen lifecycle-year plan.

No strategy outcomes, holdout returns, actual trading or database deletion are
authorized by this attempt. Dividend after-tax fields are not investor-specific
tax proof. Raw capture does not admit the economic cash/share ledger.
