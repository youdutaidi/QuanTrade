# D1 — recoverable data delivery preparation

Verdict: local archive mechanics admitted; real archive and remote asset
round-trip are not yet established by this preparation record.

- Owner: `/root`; baseline/rollback `21c816f`.
- Destination: private `youdutaidi/QuanTrade`, current account ADMIN.
- First source delivery: ordinary, non-force push succeeded. Remote
  `refs/heads/main` readback equals local
  `21c816f89c7c42a2192bc6799452c985aa8cd003`.
- Pre-push history scan: 294 unique Git blobs, largest 1,476,428 bytes, zero
  matches for the checked private-key/AWS/GitHub/OpenAI/Slack key patterns.
  Pattern screening is not proof that every possible kind of secret is absent.

## Admission actually run

- All prior 144 tests retained; 154 passed in 4.90 seconds
  (`admission-tests.log`). Synthetic WAL content survives the snapshot;
  subsequent source writes do not change that backup. Restore reproduces rows,
  refuses existing destinations, verifies inner and outer hashes, and rejects
  symlinks, path traversal, unexpected members and duplicate manifests.
- Structure gate: zero findings, package 5,601 lines / scripts 89, ratio 0.0159
  (`admission-structure.json`). Maximum function 40, class 249, module 325,
  workflow script 31 (`size_metrics.json`); no reported private-import,
  duplicate-scaffold or layering violation.
- Actual CLI refusal while implementation was uncommitted: exit 2 before
  capture (`code-identity-refusal.log`). This binds a real snapshot to committed
  code/config/tests instead of labeling a dirty tree with an older SHA.
- Local website HTTP smoke: 200. No frontend behavior or strategy parameters
  changed. A5 continues its exclusive, already-loaded source job.

## Reusable entrypoints

`qforge archive create`, `qforge archive verify`, `qforge archive restore`.
Code/config/tests must be committed before capture. Only fixed research-data
directories are selected. SQLite uses online backup, then integrity and foreign
key checks. Original databases and their active WAL files are never deleted or
copied bare. Credential-like filenames, caches, sidecars and old delivery bundles
are excluded with explicit reasons. Other source files must be stable while copied.

Archive members carry SHA256, sizes, relative paths and per-database row counts.
Restore stages verified regular files in a new directory and publishes that tree
only after matching database inventories. The separately supplied archive hash
is required; there is no automatic overwrite or broker/network operation.

## Next real attempt and claim boundary

Commit this admitted implementation, then capture an explicitly in-progress
snapshot under `research/output/delivery/data-20260826-d1` while A5 continues.
Upload the bundle and manifests as draft Release assets, download them to a
different location, and restore into a new directory. Publish only after hashes
and SQLite inventories match. Any failure gets a new attempt/output, preserving
the original local source and earlier evidence.

This is a byte-integrity and recovery gate, not global cross-database simultaneity,
data completeness, source correctness, tax validation, or investment performance.
An in-progress snapshot may include rejected trials and incomplete checkpoints;
those facts must remain visible in the release description.
