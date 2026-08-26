# D3 remote recovery gate

The existing `gh release download data-20260826-d3 --repo
youdutaidi/QuanTrade --dir research/output/delivery/roundtrip-20260826-d3`
finished successfully. No replacement download or asset overwrite was used.

The first comparison attempt looked for supporting package metadata in the bundle
directory, although those three support files live in this evidence directory.
It stopped with `FileNotFoundError` for `python-packages.json`, leaving the empty
`asset-roundtrip.json`. This was a local comparison-path error, not an archive or
network defect. It is retained; it is not a verification result.

Attempt A2 resolved each original support location and compared all six downloaded
assets with both the local bytes and recorded GitHub digests. Every comparison
passed (`asset-roundtrip-A2.json`).

The unchanged `qforge archive restore` implementation independently checked the
archive SHA256, streamed every member hash, and restored into the previously
absent `research/output/delivery/restored-20260826-d3`. All 318 files and the full
table inventories of four SQLite databases match. Integrity and foreign-key
checks pass. The result is preserved in `roundtrip-restore.json`.

This admits recoverability of the fixed D3 bytes only. It does not certify the
economic interpretation of source fields, strategy profits, or the completeness
of the in-progress dividend source capture. Final publication requires the two
proof assets and a last eight-asset remote digest check.
