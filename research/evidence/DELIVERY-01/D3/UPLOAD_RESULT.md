# D3 upload completed; full remote recovery in progress

GitHub draft release ID `376928512`, requested tag `data-20260826-d3`, frozen
target commit `ebce265f85f1ce76498104c60ccbee4ecd74a769`.
The normal `gh release create` command completed successfully. All six assets
are uploaded and their sizes/SHA256 values match the local files; see
`uploaded-assets.json` and `upload-hash-check.json`.

The archive is 1,166,904,403 bytes, SHA256
`f7ec5a289494292d8133577b0cf6cefc3508d6fd73e649eb6d56e52434a5e024`.
No duplicate release, upload retry, force push, credential upload or source-data
deletion was needed. Draft lookup used the release ID/list because the by-tag
REST endpoint did not resolve this unpublished draft.

The actual download command is running:

```bash
gh release download data-20260826-d3 --repo youdutaidi/QuanTrade \
  --dir research/output/delivery/roundtrip-20260826-d3
```

Keep it in draft until every core asset has been downloaded, SHA256-compared,
and the archive restored into a new directory with matching SQLite inventories.
Upload hashes alone do not complete the required remote recovery verification.
D2 remains the published, fully round-trip-verified snapshot in the meantime.
