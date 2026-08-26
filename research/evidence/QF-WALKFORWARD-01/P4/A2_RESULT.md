# P4 A2 — alignment stopped on suspended liquidity nulls

Implementation `515d759fae131d664fba66ba67d6786a9493003f`.
The full real-development `feature-check` exited 1 at the volume/amount guard,
before computing scores or any portfolio result. Runtime 8.71 seconds, maximum
RSS 3,153,412,096 bytes, zero swaps; macOS also reported 5,389,145,344 bytes peak
memory footprint. No row, stock, configuration or source artifact was altered.

Read-only SQL over the frozen ordinary-stock development window found:

| Trade status | Rows | Missing volume | Missing amount | Negative values |
|---|---:|---:|---:|---:|
| Suspended | 16,408 | 11,125 | 11,125 | 0 |
| Tradable | 5,799,726 | 0 | 0 | 0 |

The examples preserve raw held-flat OHLC and null liquidity for suspended dates.
The existing panel retains amount nulls; its volume transform already emits
zero for missing volume. The alignment guard incorrectly required liquidity
observations on every listed date, including known suspended bars.

Verdict: input-adapter failure, not a strategy refutation. A3 is a bounded
correction to distinguish missing **tradable** liquidity (still an error) from
known suspended nulls (retained as null). Negative values remain invalid even
when suspended. Keep every date and symbol, retain the raw database/panel hashes,
and do not fill missing amounts. The already-frozen rolling median requires a
complete observation window, so unavailable liquidity naturally prevents
eligibility; missing capacity continues to mean no fill under the existing rule.

Extend only the input guard and add targeted regressions. Retain all 190 tests
and run structure admission before a new real attempt. Full score computation,
cost and economic execution remain unverified until their respective gates run.
