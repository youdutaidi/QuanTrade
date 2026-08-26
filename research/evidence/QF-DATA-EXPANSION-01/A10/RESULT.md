# A10 result — daily inputs admitted; dividend pilot exposes a type error

## Daily gate: pass, within the documented research-input scope

The unchanged implementation `cc77d70` completed in about 80 seconds.
No daily tasks were re-downloaded: all 5430 were already successful.
The SQLite database holds 7,077,020 raw daily bars and 24,831 adjustment rows.
Calendar coverage has zero mandatory missing rows; all 2191 civil dates exist.
Five universe snapshots match exactly; two pass only under the explicitly
recorded nontradable delisting-boundary rule. No raw boundary row was deleted.

All 20 deterministic, lifecycle/board-aware source samples match both daily bars
and adjustment factors. This is **same-source replay**, not comparison with an
independent market-data vendor.

The exported panel has 7,076,844 rows, 5428 symbols and 474,278,731 bytes. The
176 raw suspended delisting-boundary rows remain in SQLite but are excluded
from the research panel. SHA256:
`5c872434d4fddf066f6fb8f8e5e151cb25b5334aefd71b6d47f67524895717dc`.
Both `market verify-panel` and the frozen study preflight passed. No strategy
outcome was computed or holdout return inspected.

Immutable completion evidence:
`../completion_runs/completion-e8d70198954a427881196268f94c32ce/`.

## Dividend pilot: raw capture passed; typed normalization needs correction

One request, `sh.600000 / 2020 / operate`, returned one row with the expected
schema and identity. Raw response SHA256:
`d56381a7d65337d5397cb07d258790f86f5f56d059541c4c91bc90d3c8708640`.
The source record's July 2020 date is legitimate for an annual request even
though it precedes this study's August start; later consumers must apply dates.

The actual row contains `dividCashStock` as a description and the after-tax
expression `0.54或0.6`. The old numeric projection retained both raw strings but
emitted nulls and invalid-field issues. The description is not malformed source
data: it was incorrectly classified as numeric by our adapter. The user's
[download plan](https://github.com/zxygithub/baostock/blob/master/docs/data_download_plan.md)
also declares `divid_cash_stock TEXT` under section 3.14.

Stop expanded capture until the text-field correction and ambiguous-tax
regression tests pass. Preserve this original request and its original derived
record; do not overwrite or erase the counterexample. The archive has 34475
pending tasks, one success and zero certified ledger events. No tax rate,
share entitlement or investment return is inferred.
