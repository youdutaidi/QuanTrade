# A13 result — conservative interpretation works; economic admission is incomplete

Owner `/root`. Real A4 command ran under committed implementation
`0ffecc839c24d6c1932cdbc665b4f2bd804a5bc7` from the repository root:

```bash
/usr/bin/time -l .venv/bin/qforge actions terms \
  --config configs/corporate_actions.json \
  --start 2020-08-25 --end 2025-08-24 \
  --output research/evidence/QF-DATA-EXPANSION-01/A13/real-preview-A4.json
```

Exit 0 means the diagnostic completed, not that its rows are ledger-ready.
At the single read snapshot `2026-08-26T07:39:28.744460+00:00`, 23,777 annual
source tasks had succeeded, one was running, and 10,698 remained pending.
Archive integrity/provenance checks found no defects. Current source ingestion
continues independently and does not retroactively change this report.

The development window has 12,687 raw rows, grouped into 12,543 security/ex-date
events. 12,348 are internally gross-source-consistent, including 124 multirow
groups represented once instead of blindly summed. 195 remain unresolved:

| Reason | Groups |
|---|---:|
| Gross cash field disagrees with the description | 161 |
| Reserve-share field disagrees with the description | 1 |
| Unsupported complete description | 14 |
| Conflicting nonblank duplicate fields | 18 |
| Missing cash payment date | 1 |

There are zero unlocated ex-dates. The 143 multirow groups include 19 not
resolved. No ambiguous tax branch was selected, no raw data was changed, no
holdout action was interpreted, and no portfolio was created. Group witness
SHA256: `e575cba6407dc872a8944d4356b2f7757be64335efefba47b66eb36562ac1462`.
Witness examples retain request IDs, raw hashes and row positions. The example
raw bytes were reread and hash-checked in `source-examples-A4.json`.

Runtime: 14.91 seconds, peak RSS 196,001,792 bytes, zero swaps. The final admission
run retained all 194 baseline tests and added 43 cases: 237 pass. Structure has
zero findings; active Python maxima function/class/module/workflow-script
40/249/325/31 lines, package/script counts 6585/89, ratio 0.0135. Existing store
state ownership and archive/status/audit commands remain intact; production code
does not import this evidence. Rollback is `198c5808`.

Follow-up A5 examined two issuer PDF documents mirrored by Sina, preserving their
original bytes, extracted text, URLs and hashes in `primary/source_documents.sqlite`.
The two documents total 495,395 bytes. SQLite integrity, file/BLOB equality and
three in-memory update/delete/duplicate refusal probes passed. Complete relevant
pages were visually checked. This is a frozen diagnostic archive, not a second
production action feed. Detailed source disagreements and limitations are in
`primary/DIAGNOSIS.md`; there are no automatic overrides of BaoStock fields.

Verdict: **supported** for conservative source interpretation and duplicate
safeguards; **incomplete** for company-action economic admission. Latest recorded
capture status at 07:47:39Z is 27,226 succeeded tasks and 20,215 raw events with one
source run still active (`current-capture-A5.json`). All `ledger_ready` flags are
still false. Verified strategy count remains zero.

Next discriminator: finish the unchanged fixed source plan, rerun the complete
archive audit, and reconcile unresolved economic terms with archived issuer
evidence. Keep gross cash, reference-price adjustments, investor class/tax,
fractional allocation and actual settlement separate. Do not relax the exact
agreement check or force an account replay just to produce a return number.
