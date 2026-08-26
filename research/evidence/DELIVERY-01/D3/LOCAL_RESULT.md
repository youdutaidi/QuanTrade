# D3 local snapshot passed; remote delivery still pending

- Source commit: `ebce265f85f1ce76498104c60ccbee4ecd74a769`, pushed and
  read back at `refs/heads/main` before uploading the data.
- Capture: 2026-08-26T06:43:57.146604Z to 06:44:18.982607Z, separate
  per-file/per-database instants. 318 files, 2,382,210,300 uncompressed bytes.
- Archive: 1,166,904,403 bytes, SHA256
  `f7ec5a289494292d8133577b0cf6cefc3508d6fd73e649eb6d56e52434a5e024`.
- Existing archive verifier passed every member hash and exclusion/path check.
- Four SQLite backups passed integrity, foreign keys and table inventory capture.
  Source databases are unchanged and ongoing action ingestion continues.
- Secret-pattern screening examined 319 members including the embedded manifest:
  no known strong credential-pattern findings. This is not a guarantee against
  every possible secret. Cookie caches and transient sidecars are excluded by
  the separate enforced path policy.
- Market database: 7,077,020 daily bars, 24,831 adjustment rows, 5430 completed
  tasks. Panel SHA256 matches the A10-admitted full research input.
- Minute database: 116,160 real bars. Study database: 145 synthetic runs and
  7356 ledger events. These are not certified real-market performance.
- Action database: 34,476 planned tasks, 721 request records, 571 source events.
  Capture is incomplete; later live rows are not part of this fixed snapshot.

The new D3 prerelease is being created in **draft** state. Do not publish until
all uploaded core assets have been downloaded and the archive restored into a
new directory with matching hashes and SQLite inventories. D2 remains published.
