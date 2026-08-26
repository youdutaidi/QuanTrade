# A12 result — real archive consistency supported, capture incomplete

Frozen implementation `4bdf63cc1386ce74d23dccd3e84948589e82c489`.
Command:

```bash
/usr/bin/time -l .venv/bin/qforge actions audit \
  --config configs/corporate_actions.json \
  --output research/evidence/QF-DATA-EXPANSION-01/A12/live-audit-A2.json
```

At 2026-08-26T06:57:59Z, one read snapshot contained 5364 successful annual
requests, one running and 29111 pending. All 5364 successful raw responses passed
hash, schema, identity and row-count checks. 3758 source events and 1985 queried
empty years were retained; 3757 current derived rows matched raw re-normalization.
The single legacy projection is explicitly not certified or consumed and its
historical bytes remain untouched. No archive/provenance defects were found.

The result is `capture-incomplete`, exit 2, intentionally: the remaining planned
tasks cannot be ignored. Wall time 3.35 seconds, maximum RSS 167,149,568 bytes,
zero swaps. No source request or database mutation was performed by the audit.
The running A11 process continued under its original loaded adapter.

The audit exposes unresolved economic inputs: 3731 ambiguous after-tax fields,
29 missing gross cash values, 13 missing payment dates, blank share-related
fields, and 83 source rows marked with a repeated ex-date. It also identifies
505 events outside the study dates because the source is queried annually.
These counts are not automatically converted into zero amounts, payment dates,
tax rates, or investable returns.

`duplicate-source-examples.json` inspects only development dates and preserves
the first eight repeated-date groups. Some rows are exactly duplicated; others
have blank versus populated values or differing descriptive/announcement fields.
Naively adding every row could double-count dividends. No source row was removed,
merged, or used to rank a strategy in this attempt.

Continuity: all 171 baseline tests retained unchanged; full suite 186 passed.
Structure: zero findings, maximum function/class/module/script 40/249/325/31,
script/package ratio 0.0141. The new audit witness is 199 lines including its
module docstring (the 198-line wording in ADMISSION excluded that one line).
One archive writer remains; no downloader or accounting state was duplicated.

Owner `/root`; public entrypoint `qforge actions audit`, rollback `6c28760`.
Verdict: supported for same-source raw archival consistency only. Continue the
fixed capture, then audit full coverage. Economic action resolution, investor
tax, rights issues, market execution, real strategy returns and holdout remain
unadmitted. No verified strategy was added.
