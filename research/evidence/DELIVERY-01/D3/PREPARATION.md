# D3 — complete daily input plus in-progress action capture

Baseline `52a55aa`; unchanged admitted archive implementation. All 171 retained
and new tests pass. Destination remains the user's private QuanTrade repository.
Do not replace or delete D2, alter remote history or remove local data.

The new snapshot must include the admitted 7,077,020-row raw daily database,
the 7,076,844-row fingerprinted panel, the real 116,160-row five-minute sample,
the retained source files, current research outputs/evidence and every local
research database selected by the fixed allowlist. The raw dividend archive is
still being collected; its captured checkpoint must be clearly labeled partial.
Source/cache exclusions are unchanged. Do not copy live SQLite sidecars.

Use consistent online SQLite backups. Other files must be byte-stable while
copied; a changing file fails the attempt instead of silently changing its hash.
Capture times are per-file/database, not a globally atomic collection.

Validation sequence: local archive member/hash verification, upload to a new
draft prerelease, download every core asset, compare SHA256, restore to a new
directory, match SQLite integrity/foreign keys/table inventories, then publish
with proof assets. Keep the source commit fixed in the release tag.

Restore documentation must distinguish original evidence paths from a new
machine's paths. After safe placement in a fresh clone, a relocated daily input
must use the existing `market complete` command to regenerate its local
fingerprinted manifest; do not edit historical hashes or pretend old absolute
paths are portable. This may replay source samples but does not re-download
already successful daily tasks.

This delivery milestone does not certify cash/share economics, market execution,
holdout returns, forward paper trading or a 100% annualized strategy.
