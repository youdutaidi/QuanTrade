# QF-WALKFORWARD-01 — P1 preparation gate

Date: 2026-08-26. Owner: `/root`. Baseline: `f1d17d1`.

Verdict: configuration and synthetic semantics admitted; market experiment not
started. QF-DATA-EXPANSION-01 remains the sole active empirical experiment.

## Frozen decision

The 144 candidates specified before outcomes are now executable signal
definitions: 16 distinct signal settings crossed with nine rebalance/holding
schedules. Residuals remove a 60-session lagged OLS intercept and market beta;
this is not a Fama-French residual-momentum replication. Three chronological
development folds select the candidate; they are not unbiased winner OOS.
Only the unopened final holdout can provide that evidence.

Config SHA256:
`f946362d7d5e71e2e023e5412cd3024bada5edcec5eddd1b18737eaf2afdeae4`.

`frozen_plan.json` contains all 144 IDs, parameters, dates and the fingerprint.
The CLI refuses to overwrite an existing plan. It reads no market outcomes.

## Checks actually run

- `.venv/bin/python -m pytest -q`: **92 passed**, including all 63 retained tests.
- Structure gate: **pass**, zero findings; 3,986 package lines, 89 workflow lines.
- Every distinct signal setting: prefix invariance on deterministic synthetic data.
- Known linear beta/intercept removal, no same-day beta fit, compound reversal,
  lagged liquidity, missing/ST exclusion, stable ties and idle cash slots checked.
- Stamp-duty and transfer-fee effective dates, ST change on 2026-07-06,
  STAR 200-share minimum/one-share increments, odd-lot liquidation, available
  T+1 quantity cap, adverse slippage and limit rejection checked.
- Monetary fees and exchange limits use decimal half-up cent rounding;
  adverse slippage is rounded against the trader.
- `qforge minute status`: retained 116,160 real five-minute bars, 10 symbols,
  242 sessions; this command did not rerun or promote the rejected minute strategy.
- Local website HTTP check: **200** at `http://localhost:3000/`.

## Data download continuity

The existing single BaoStock downloader was left running, without another
concurrent source session or any data deletion. A local inventory snapshot at
2026-08-26T04:57:15Z contained 5,344,919 daily bars and 18,446 adjustment-factor
rows, with 4,027 / 5,430 tasks succeeded; one source receive failure remained
eligible for the existing retry pass. This is an inventory count, not full data
admission. Downloading continues after this snapshot.

## Rules and scope

- [Exchange fee structure](https://one.sse.com.cn/onething/gptz/): brokerage
  commission is modeled as all-in for handling/regulatory fees to avoid counting
  them twice. The chosen 0.03% rate is a study assumption, not the user's broker quote.
- [Tax authority stamp-duty notice](https://shanghai.chinatax.gov.cn/gate/big5/shanghai.chinatax.gov.cn/tax/zcfw/zcfgk/yhs/202308/t468451.html)
  and [broker's transfer-fee implementation notice](https://www.xcsc.com/main/a/20220429/1022871784.shtml)
  support the dated cost schedules; the latter is not claimed to be the original
  ChinaClear circular.
- [SSE ST rule change](https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20260424_10816474.shtml),
  [SZSE change notice](https://www.szse.cn/lawrules/service/member/t20260630_621404.html),
  [STAR quantity rules](https://edu.sse.com.cn/tib/ysptj/c/4869120.shtml),
  and [ChiNext rules](https://investor.szse.cn/knowledge/t20200721_579820.html)
  inform the board/date-specific primitives.

None of these checks proves actual opening-auction liquidity. The 0.5% lagged
daily-volume cap is an approximation, and exceptional no-limit sessions require
separate evidence. The current primitives enforce an available-inventory cap;
the future portfolio state machine must also test its actual T+1 rollover.
The adjusted-price signal chain is not a cash/share corporate-action ledger.
Portfolio replay, source-complete inputs, independent economic P&L, multiple-test
inference and genuine forward paper trading remain uncompleted gates. No
return or >100% annualized strategy claim is made in P1.

Next falsifier: refuse incomplete or changed input manifests, then reconcile a
tiny synthetic order ledger before any full-universe market-outcome run.
