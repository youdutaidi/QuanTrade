# A14 result — complete unresolved queue, no economic admission

Admitted code `8b5ee048a55dcc0ae4b84aa26891ef3685dfe516`; owner `/root`.
The frozen development-only command in PREPARATION.md completed in 18.45 seconds,
with 211,746,816 peak resident bytes and zero swaps. All 252 tests passed before
this run, including all 237 retained cases; structure findings were zero.

`real-triage-A2.json` is one read snapshot at 2026-08-26T07:54:42.959741Z.
It checked 30,386 successful requests, with one running and 4089 pending;
archive integrity and raw provenance passed. This was not a completed capture.
The development window has 15,972 raw rows, 15,790 ex-date groups, 15,369
gross-source-consistent groups and 421 unresolved groups. Of 180 multirow
groups, 157 resolved once without summation. Unlocated dates: zero.

The unresolved queue retains all original records, request IDs, response hashes
and row indices. Reasons: 397 gross-cash disagreements, one reserve-share
disagreement, 13 conflicting descriptions, eight conflicting after-tax fields,
one unsupported description and one missing payment date. The group fingerprint
is `70588a2ebb0311393ccb1ab7814388d68400541ad38ca2a37d275ea0a51a55cf`.
More source coverage than A13 means their unresolved counts are not a same-input
comparison of parser quality.

An additional read-only Decimal diagnostic, summarized in
`precision-diagnostic-A3.json`, found that 393/397 cash differences are at most
0.000001 per share. Only 369 match six-decimal ROUND_HALF_UP; 24 other small
differences are downward half-unit ties. The remaining four are substantive:
600803 on two dates, 001323 and 002352. Small magnitude is not proof that either
field is authoritative. No numeric tolerance, source preference, correction,
tax branch or acceptance policy changed. Every conflict remains unresolved.

The sole unsupported description is 688466 on 2023-07-17:
`10送2（含税，扣税后-0.2元）`. Its signed after-tax suffix lies outside the
admitted grammar. It is not converted to positive cash or silently discarded.
The original row is retained for a separately scoped parser/source decision.

Verdict: representation and complete diagnostic export are supported. All
`ledgerReady` and `investorTaxVerified` flags remain false. No account, strategy
return, winner selection or holdout performance was computed. The running A11
capture retained its original provider, store, adapter, scope and session.
