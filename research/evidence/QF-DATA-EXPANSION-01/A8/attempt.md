# QF-DATA-EXPANSION-01-A8

Baseline: `b6d7f5d`; owner `/root`; local repository unchanged.

The A7 live audit read inventory before opening its separate coverage read
transaction. Concurrent ingestion advanced by one successful task between the
two snapshots. This did not produce a ready claim, but made one report's counts
inconsistent. Its original evidence remains retained under A7.

The audit now passes its own read connection to `MarketDataStore.status`.
Inventory, calendar, coverage and integrity all observe one SQLite snapshot.
The regression test commits a missing bar using a second WAL connection during
the audit and verifies that every reported logical count remains on the initial
snapshot. The new row is visible only to a subsequent reader.

- Structure: zero findings; 3,576 package lines / 89 script lines; ratio 0.0249.
- Semantics: all 63 retained and additive tests passed.
- Real-data check: `live_data_audit.json`; final source replay still pending.
- No prices, reference observations or download checkpoints were deleted or
  changed by this correction. The A5 single source process remains active.
- Baseline daily/minute/validation tests are retained. Local site HTTP smoke
  returned 200. No strategy or return claim is admitted by this data audit.
