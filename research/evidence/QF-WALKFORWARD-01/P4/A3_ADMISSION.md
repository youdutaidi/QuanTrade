# P4 A3 — suspended liquidity guard correction admitted

All 194 tests pass in 8.44 seconds, retaining all 190 prior cases. New tests
show that suspended volume/amount nulls remain null and cannot create eligibility
or execution capacity, while missing tradable liquidity and negative suspended
liquidity still fail. The source database, frozen panel, stock/date coverage,
rolling equations and all 144 candidate definitions are unchanged.

Structure gate passes with zero findings: 6383 package lines, 89 script lines,
ratio 0.0139. This is a two-line net change within the existing alignment guard,
not a new state machine, alternate factor path, script or scientific axis.
The retained tests cover both causal score behavior and the account/independent
ledger audit. No source action is reinterpreted by this change.

The next admitted attempt is the same full-development feature check in a new
output directory. No smaller stock pool, zero-filled amount field, return
ranking, tax choice or holdout calculation is allowed. Preserve any next failure
and do not use this guard correction as proof that the full calculation passed.
