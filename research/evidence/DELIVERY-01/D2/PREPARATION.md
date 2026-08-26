# D2 — session-cache exclusion correction

Baseline/rollback: `27d9fe7`; owner `/root`. Same fixed delivery scope and
in-progress snapshot definition as D1. No source prices are removed, no new
BaoStock session is opened, and no strategy definition changes.

The D1 actual capture exposed a missing exclusion: Yahoo's `yf_cache` contains
provider cookies and timezone cache, not the downloaded price archive. D2 excludes
that directory and explicit cookie/credential filenames. Verification and restore
also reject those paths; this is not merely a release-note warning.

Admission: all prior 154 tests retained; 156 passed in 4.87 seconds
(`admission-tests.log`). Structure gate reports zero findings, 5,608 package lines
and 89 script lines, ratio 0.0159 (`structure.json`). The change adds seven lines
to the previously admitted capture/recovery modules and no new state owner,
runner, private import or scientific choice axis.

The real D1 archive was checked under the corrected verifier with its actual
SHA256: exit 2 before extraction, explicitly rejecting session-cache/sidecar
entries (`old-cache-archive-refusal.log`). `source-selection.json` records the
new read-only selection and each exclusion; it is not a completed backup.

Commit this admitted correction, then create D2 in a new output directory.
The D1 bundle stays local and quarantined; no data has yet been uploaded.
Publish a D2 prerelease only after a fresh GitHub download passes member hashes
and non-overwriting SQLite restoration. The first snapshot is explicitly partial,
and neither byte integrity nor source capture implies verified performance.
