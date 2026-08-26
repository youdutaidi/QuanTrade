# A14 — complete unresolved queue and order-independent named legs

Owner `/root`, baseline `d25005daf14eec51187da6fa99a74c39add9e4ba`.
Scope is frozen in `research/README.md`. No strategy parameters, data scope,
download service, source store, provider session or investor-tax policy changes.

One parser now recognizes unique explicitly named cash/bonus/reserve legs in any
order within a complete per-ten-share plan. Repeated legs, incomplete units,
unsupported suffixes and every nonblank numeric disagreement still fail. This
corrects the observed reserve-before-bonus syntax without introducing a numeric
tolerance or selecting a source correction. Gross terms remain ledger-unready.

The existing single-snapshot preview gains opt-in `--include-unresolved` output,
containing all unresolved in-window groups, every original row, request ID,
response SHA256 and row position. Default output stays summary-only. Both modes
produce the same counts and group fingerprint. Resolution version is now 2.
The witness owns provenance only; the existing archive remains the only raw-data
state owner, and no economic account is instantiated.

Actual admission commands:

```bash
.venv/bin/python /Users/cailingling/.codex/skills/research-code-evolution-guard/scripts/structure_gate.py \
  . --package qforge --scripts research/data_workflows \
  --json-out research/evidence/QF-DATA-EXPANSION-01/A14/structure-A1.json
.venv/bin/python -m pytest -q
```

Structure passes with no findings. Active Python maxima: function 40, class 249,
module 325, workflow script 31 lines; package 6599, scripts 89, ratio 0.0135.
All 237 previous tests are retained unchanged; 15 new cases produce 252 passes in
7.59 seconds (`tests-A1.log`). They cover six permutations, duplicate/incomplete
legs, observed reverse-order syntax, strict small/large disagreement refusal and
complete unresolved raw provenance without out-of-window leakage. No duplicate
scaffold, cross-private import or unused public export was introduced.

After committing this admitted candidate, run the frozen development-only
command recorded in the canonical contract, under `/usr/bin/time -l`, into the
new `real-triage-A2.json` and corresponding log. Stop on archive/provenance failure;
otherwise classify unresolved cases without treating error tolerance, higher
cash, lower tax or simpler rounding as source truth. Rollback remains `d25005d`.
