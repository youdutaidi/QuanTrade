# A13 — source-consistent gross terms, not an economic ledger

Owner `/root`; baseline `198c5808f2a5a780d9ffb9162faf5de887922817`.
Canonical scope and admission are in `research/README.md`. The A11 source job
continues with its previously loaded adapter. No provider, normalization, store,
source scope, frozen candidate configuration or raw database was changed here.

Pure source interpretation accepts only a complete per-ten-share description,
uses exact Decimal legs, and checks every nonblank gross numeric field. Missing
legs become zero only through the recognized complete plan, not because the
corresponding numeric field is empty. Nonempty duplicate fields must all agree;
records are never summed or selected by recency. Unknown plans and chronology
gaps remain unresolved. Source tax alternatives are never selected. All outputs
keep `ledgerReady=false` and `investorTaxVerified=false`.

The existing archive auditor now exposes a public connection-level composition
function, requiring an explicit transaction. The preview audits and interprets
inside the same SQLite read snapshot. It does not initialize or write an account,
change source rows, calculate returns, or rank strategies. The real preview window
is fixed to 2020-08-25 through 2025-08-24. Out-of-window actions are not interpreted;
invalid/unlocatable ex-dates remain explicit unresolved counts.

Admission: all 194 baseline tests are retained unchanged. Final run has 237 passing
tests in 9.42 seconds (`admission-tests-A3.log`), including 43 additive adversarial
cases. The first 235-test run had a log-capture path error because this evidence
directory did not yet exist; stdout showed passing tests but no log was saved.
A2 reran all 235 successfully with a saved log. Two further cases check unlocated
dates and partial-capture nonpromotion, resulting in the final 237-test run.

The first two structure reports incorrectly omitted the real workflow directory
and reported zero script lines. They are retained as incomplete-scope checks.
Correctly scoped A3/A4 include `research/data_workflows`: no findings; maxima
40/249/325/31 function/class/module/script lines, 6585 package lines and 89 script
lines, ratio 0.0135 (`size-metrics-A4.json`, `structure-A4.json`). The pure source
interpreter owns no mutable state or I/O; witness code owns hashes/provenance;
the existing store remains the sole raw-archive state owner. No private import,
new duplicate scaffold, second account owner or zero-consumer export was added.

The frozen strategy SHA remains
`f946362d7d5e71e2e023e5412cd3024bada5edcec5eddd1b18737eaf2afdeae4`.
Rollback target is the baseline. Promote `qforge actions terms` with the retained
archive/status/audit entrypoints; its scope is source interpretation only.

Next exact discriminator, after committing this admitted implementation:

```bash
/usr/bin/time -l .venv/bin/qforge actions terms \
  --config configs/corporate_actions.json \
  --start 2020-08-25 --end 2025-08-24 \
  --output research/evidence/QF-DATA-EXPANSION-01/A13/real-preview-A4.json
```

Stop on archive/provenance failure. Otherwise inspect the unresolved groups;
passing the parser does not admit investor taxes, fractional-share allocations,
rights issues, actual historical publication, official ex-prices or economic P&L.
No real preview has run at this preparation point.
