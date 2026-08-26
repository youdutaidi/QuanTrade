# P4 result — real full-development signal preparation passed

Final admitted implementation `7ccec1f55e9729e0a4f4c5a057adc27c61f8d57e`.
Actual command:

```bash
/usr/bin/time -l .venv/bin/qforge walkforward feature-check \
  --config configs/walk_forward.json \
  --plan research/evidence/QF-WALKFORWARD-01/P1/frozen_plan.json \
  --output research/evidence/QF-WALKFORWARD-01/P4/real-development-A6
```

A6 completed 5,820,982 development rows, 5341 historically listed ordinary
A-share stocks and 1212 sessions, 2020-08-25 through 2025-08-22. All 16 frozen
score settings for the 144 unchanged candidates have finite eligible scores,
matching axes, no infinities and no finite values outside eligibility. Warm-up
and liquidity-missing cells remain unavailable, not fabricated observations.

Wall time 19.97 seconds. Internal timings: load 0.91s, alignment 10.18s, shared
score computation 8.36s. Peak RSS 3,662,610,432 bytes, zero swaps; separate macOS
peak memory footprint 5,684,811,320 bytes. This is a measured feasibility check,
not a synchronized performance benchmark or portfolio-return measurement.

The full input panel SHA remains
`5c872434d4fddf066f6fb8f8e5e151cb25b5334aefd71b6d47f67524895717dc`;
study SHA remains `f946362d7d5e71e2e023e5412cd3024bada5edcec5eddd1b18737eaf2afdeae4`.
Reference-calendar/lifecycle SHA is
`834d66b1cd7d90e30ac46e0117f7a0363454a18e0f6f9f880af5601189ad18d8`.
Predicate pushdown excludes holdout values before DataFrame creation. No stock
pool was reduced, no source amount was zero-filled and no data was deleted.

Preserved attempts: A2 exposed suspended amount nulls; A3 corrected only the
input guard with negative/tradable-null regressions. A4 completed calculations
but exposed an evidence-merge state-label collision; A5 reproduced and fixed
that report bug. A6 emits the correct workflow state. Its input/reference/study
identities and all 16 score-coverage summaries match A4, as recorded separately;
this comparison is not a claim of an independent elementwise factor audit.

Maintainability and continuity: 194 tests pass, preserving prior coverage and
strengthening the workflow-state fixture. Structure findings zero; maximum
function/class/module/script lengths 40/249/325/31; 6383 package lines, 89 workflow
script lines, ratio 0.0139. One source-input adapter, one pure signal engine and
one composition workflow remain; no duplicate state owner, private import or
20-line scaffold finding. Minute data remain 116,160 real bars; local site HTTP
smoke returns 200. No account was created by this preflight.

Owner `/root`; public command `qforge walkforward feature-check`; original
rollback `64f3bbf` and subsequent attempts remain in Git and immutable evidence.
Verdict: supported for real full-development input/feature preparation only.
Company-action resolution, economic cash/share consumption, actual portfolio
returns, candidate selection, multiple-testing controls, holdout and genuine
forward paper trading remain unadmitted. Verified-strategy count stays zero.
