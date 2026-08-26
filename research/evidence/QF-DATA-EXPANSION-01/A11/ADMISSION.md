# A11 admission

- All 171 tests pass, including all 168 retained tests and three new source-text,
  ambiguous-tax and non-mutating legacy-reparse cases. Hash-tampering rejection
  also applies to the reparse entrypoint.
- Structure gate: pass, zero findings; 6074 package lines, 89 workflow-script
  lines, script/package ratio 0.0147.
- Real reparse: the original raw SHA256 remains `d56381a7...8640` and the
  historical projection SHA256 remains `cf8c2017...5e06`. Full digests and
  corrected values are in `real-renormalization.json`.
- Continuity: successful source requests are not repeated; old derived records
  are not rewritten; unknown numeric values remain null, and both tax/ledger
  verification flags remain false. No market-data module or strategy changed.
- Maintainability: source typing stays in the existing pure normalization
  module; SQLite remains owned by `ActionStore`. One small read-only adapter
  reconstructs a DataFrame from hash-checked raw data and calls that normalizer.
  No second store, new configuration branch, duplicate calculation, migration,
  evidence-writing math helper, large script or circular dependency was added.

The bounded nine-request source continuation is admitted. Bulk capture and
economic cash/share consumption are not admitted by these tests alone.
