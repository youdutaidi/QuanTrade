# D2 — upload succeeded, full restore verification pending

Code commit `5368a6fe77aacec86e23a831338d82bd5b2a3ad5` was pushed normally;
GitHub's `refs/heads/main` was read back and matched. The source remains local.

The draft release `data-20260826-d2` contains six successfully uploaded assets:
`quant-data.tar.gz`, `manifest.json`, `delivery.json`, `RESTORE.md`,
`python-packages.json`, and `runtime.json`. `remote-draft.json` records GitHub's
asset IDs, sizes, digests, draft state and exact target commit.

Archive: 636,315,381 bytes; 121 captured research files; SHA256
`0799eda5a445a1228f63168a304355e64ae821b84799e5099d15ddc55f34c94f`.
GitHub reports the identical digest. Local member verification passed
(`local-byte-verification.json`) and the additional strong-key-pattern scan found
zero matches across 122 members including the manifest (`content-screen.json`).
These are bounded integrity/security checks, not a guarantee about every secret
format or the financial correctness of the source data.

The archive contains three SQLite online backups, each with integrity/foreign-key
checks passing at capture. The daily backup has 6,065,746 daily bars and 20,175
adjustment factors; the minute backup has 116,160 bars; the walk-forward backup
contains one synthetic run and 12 ledger events. Capture was 2026-08-26
05:53:42–05:53:57 UTC. Acquisition was still running, so this is explicitly
in-progress and not the final full dataset.

Both JSON manifests have been downloaded from the draft and `cmp` matches the
local originals. The archive is still downloading to
`research/output/delivery/roundtrip-20260826-d2/quant-data.tar.gz`; the active
download command also requests the restore guide and runtime metadata.
No complete round-trip restore is claimed yet. Keep the release as a draft.

Next exact step after the download exits successfully:

```bash
.venv/bin/qforge archive restore \
  --bundle research/output/delivery/roundtrip-20260826-d2/quant-data.tar.gz \
  --sha256 0799eda5a445a1228f63168a304355e64ae821b84799e5099d15ddc55f34c94f \
  --output research/output/delivery/restored-20260826-d2
```

Use a new output directory. Check every restored database inventory against the
embedded manifest, retain the result, compare all downloaded support-file hashes,
then publish as a prerelease with explicit incomplete-data and zero-verified-
strategy warnings. Do not overwrite the live local databases or publish the
quarantined D1 bundle. A5 remains the sole active BaoStock downloader.
