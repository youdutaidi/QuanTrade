# D2 — published recoverable in-progress snapshot

Verdict: **remote byte-integrity and recovery gate passed**; not complete data or
strategy admission. The first user-requested repository data delivery is usable.

- Release: https://github.com/youdutaidi/QuanTrade/releases/tag/data-20260826-d2
- Published at 2026-08-26T06:28:50Z; prerelease, not Latest, no longer a draft.
- Frozen code/tag: `5368a6fe77aacec86e23a831338d82bd5b2a3ad5`; remote tag API readback matched.
- Archive: 636,315,381 bytes, SHA256
  `0799eda5a445a1228f63168a304355e64ae821b84799e5099d15ddc55f34c94f`.
- Six core/support assets were downloaded to a separate directory and matched
  GitHub's digests (`asset-roundtrip.json`). All 121 archive files passed their
  embedded checksums; three databases restored into a new, absent directory and
  passed integrity/foreign-key checks plus complete table-row inventory comparison
  (`roundtrip-restore.json`). No live database was overwritten.
- Added two proof assets, then checked all eight remote asset digests and the
  recovery result before publication (`publish-gate.json`, `prepublish-assets.json`).
- Provider cookies are absent. The rejected D1 bytes remain local and quarantined;
  they were never uploaded. The original local databases remain available.

This fixed snapshot includes 6,065,746 daily bars and 116,160 five-minute bars at
its capture time, plus the then-current synthetic ledger and research artifacts.
The continuing local acquisition later reached more rows, which are not silently
claimed to be included in this earlier archive. Full data completion, company
actions and verified strategy returns remain open. Recovery instructions and
runtime/package metadata are attached to the release.

Engineering admission was 156 tests and zero structure findings in D2; the
subsequent strategy-executor preparation has its own P3 evidence. Neither count
is evidence of profitable investment performance.
