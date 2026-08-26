# D3 — published and remote-recovery verified

Verdict: supported for byte-integrity and local recovery of the fixed snapshot.
It does not complete data expansion or strategy validation.

- Published release: https://github.com/youdutaidi/QuanTrade/releases/tag/data-20260826-d3
- Published at `2026-08-26T07:37:11Z`, draft false, prerelease true, not Latest.
- Tag resolves to `ebce265f85f1ce76498104c60ccbee4ecd74a769` (`published-tag.json`).
- Archive: 1,166,904,403 bytes, SHA256
  `f7ec5a289494292d8133577b0cf6cefc3508d6fd73e649eb6d56e52434a5e024`.
- Six core assets were downloaded and compared with local and GitHub hashes;
  318 members and four database inventories restored into an absent directory.
- Two recovery proof assets were added, then all eight remote sizes and digests
  checked before publication. Evidence: `asset-roundtrip-A2.json`,
  `roundtrip-restore.json`, `publish-gate.json`, `published-release.json`.
- Original local data, old D2 release and failed diagnostic attempts are preserved.

Contents include the full admitted daily input (7,077,020 raw bars), the existing
116,160-bar five-minute pilot, 145 synthetic study runs, and the raw action archive
at capture (721 requests, 571 events). Continuing action ingestion and later code
are not included retroactively. See `RESTORE.md` for new-path manifest rebuilding.
No source session was started for this recovery check and no portfolio return
was computed. Current validated-strategy count remains zero.
