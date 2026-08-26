# D1 real capture — protocol-invalid for delivery

The consistent SQLite capture and compression completed locally with 116 files,
624,914,575 archive bytes and SHA256
`67d21ac62ddfd6417a08869e8c0bb329f1f420b867d254bbbd015dad95a7fb91`.
However, the progress/manifest review found `research/data/yf_cache/cookies.db`
and the associated Yahoo timezone cache in the selected files.

The source-selection policy did not adequately exclude provider session caches.
Therefore this artifact is **not approved for upload**, even if byte integrity
would pass. No Release existed and no data asset was transmitted. A local
`QUARANTINED.md` marks the generated D1 directory; original source data remains
untouched. No cookie contents were printed to the user or committed to Git.

Next attempt D2 adds explicit provider-cache exclusion and refuses such entries
in the verifier/restorer as well. Retain this attempt record; do not relabel D1
as a successful delivery or reuse its bytes for publication.
