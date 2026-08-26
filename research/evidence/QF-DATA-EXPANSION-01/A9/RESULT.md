# A9 — lossless annual dividend capture preparation

Verdict: **capture mechanics supported; real source coverage not yet admitted**.
This is a bounded implementation attempt under the existing data experiment,
not a strategy experiment or a result claiming 100% annualized performance.

## Identity and boundary

- Owner: `/root`; local repository `/Users/cailingling/Desktop/quant-intelligence-lab`.
- Baseline/rollback identity: `7a1fe0b`.
- Provider: BaoStock 0.9.3; adapter identity is frozen in `source-adapter.json`.
- Configuration: `configs/corporate_actions.json`, referencing the unchanged
  raw daily window 2020-08-25 through 2026-08-24.
- Planning scope: 5,424 A-share lifecycles, 34,476 code/year queries; scope hash
  `5983b1dc73827d5cbe7da6787f5c05858e1e38e1fdbe00291ba29c6079cc5ad8`.
- Running A5 source job remains on its already-loaded code. No new live
  dividend query was made and no `qforge_actions.sqlite` was created.

## Evidence actually obtained

1. `pytest -q`: initial 142 tests passed; final admission 144 passed in 5.21 s
   (`tests.log`, `admission-tests.log`). All prior 115 tests remain present.
2. Structural gate: zero findings, 5,252 package lines / 89 workflow lines,
   script/package ratio 0.0169 (`admission-structure.json`). Maximum function
   40, class 249, module 325, script 31 lines (`size_metrics.json`). No reported
   private import, duplicate scaffold or layer violation.
3. `qforge actions plan --preview --config configs/corporate_actions.json`
   reads real security lifecycle metadata without prices, network or checkpoint
   mutations (`lifecycle-preview.json`). Current listing status is not used to
   remove delisted securities; all overlapping years are queried, including
   years that may contain no dividend.
4. `qforge actions download --config configs/corporate_actions.json --max-tasks 1`
   exited 2, before archive initialization or source login, because the daily
   source job is active (`active-source-refusal.log`). This is an expected
   admission refusal, not evidence of a provider outage.
5. Retained minute status: 116,160 bars, 10 symbols, 242 sessions
   (`minute-continuity.json`). Local HTTP smoke returned 200.
6. The frozen strategy configuration remains SHA256
   `f946362d7d5e71e2e023e5412cd3024bada5edcec5eddd1b18737eaf2afdeae4`.
7. Live daily snapshot at 05:36:10 UTC: 5,550,021 bars, 4,173 succeeded tasks,
   one retryable failed task, 1,256 not yet completed (`market-status.json`).
   This snapshot is not final coverage or strategy admission.

## Admitted reusable behavior

- `qforge actions plan/download/status` and the separate action archive schema.
- One actual request increments one attempt; failed/interrupted request history
  is retained. Successful raw envelopes, original string precision, field order,
  request identity, hashes and explicit empty-year responses persist atomically.
- Parsed missing/invalid values remain null with issue labels; duplicate ex-date
  rows remain visible. The archive always keeps `ledger_ready=0`.
- Each run records daily-input evidence, scope hash, provider version and adapter
  fingerprint. Reusing a changed scope refuses instead of reusing checkpoints.
- Per-archive job exclusion protects recovery; shared anonymous-source exclusion
  is checked before both new daily and minute logins. Cross-process exclusion,
  login-failure cleanup and logout-failure cleanup passed fixtures.

The existing A5 process predates the source lock. The separate active-run check
therefore remains necessary until A5 exits. This change does not retroactively
repair or recertify the legacy minute execution model.

## Not established / next exact gate

Raw capture is not complete corporate-action coverage. Rights issues, missing
records, revised announcements, cash/share interpretation, shareholder-specific
tax, fractional entitlements and mapping to raw reference prices remain open.
The provider's after-tax field is never silently accepted as the user's tax result.
The installed SDK's `query_dividend_data` defines `yearType="operate"` as the
ex-dividend year; the field inventory also follows the user-provided
[BaoStock download plan](https://github.com/zxygithub/baostock/blob/master/docs/data_download_plan.md).

After A5 finishes: run the current market completion/replay/export gate; verify
its fingerprint; then run a bounded 10-query real dividend pilot. Inspect actual
schemas, empty responses, raw hashes and date/cash/share coverage before allowing
the full capture. A schema mismatch or identity error stops that pilot. Until
then this is admitted code preparation, not source validation or economic P&L.
