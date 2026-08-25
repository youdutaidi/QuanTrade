# Q-Forge research contract

## AH-01 baseline

- Evaluation window: 2025-08-25 through 2026-08-24.
- Design/diagnostic split ends 2026-02-24; the second half is shown separately.
- Universe: current CSI 300 and CSI 500 constituents downloaded from the official CSI files. This is a deliberate cheap first screen and is **not** survivorship-safe.
- Market data: adjusted daily OHLCV from Yahoo Finance; membership from China Securities Index.
- Signal: previous close and older data only; rebalance at the next adjusted open.
- Cost proxy: 15 bps on buys and 20 bps on sells, including a conservative slippage allowance. It does not yet model limit-up/limit-down non-fills or minimum broker commissions.
- Strategy family: long-only price momentum, risk-adjusted momentum, breakout and reversal-within-trend; top 3/5/10, equal/inverse-volatility weights, weekly/biweekly/monthly rebalance, optional 120/200-day market regime filter.
- Forbidden inference: a profitable curve is not evidence that the same return was achievable live. The current-constituent bias gate fails by construction.

Run in order:

```bash
.venv/bin/python research/build_factor_catalog.py
.venv/bin/python research/fetch_market_data.py
.venv/bin/python research/run_backtests.py
```
