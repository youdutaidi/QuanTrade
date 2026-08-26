# P5 — prior-outcome exposure falsifies the untouched-holdout claim

Read-only claim audit on 2026-08-26; owner `/root`, code baseline
`8b5ee048a55dcc0ae4b84aa26891ef3685dfe516`. No new portfolio replay, candidate
selection, market window, strategy parameter or source-data mutation.
QF-DATA-EXPANSION-01 remains the sole active empirical experiment.

## Decision and direct counterexample

The P1 specification reserves 2025-08-25 through 2026-08-24 and calls it a
`single_untouched_final_holdout_only` source of unbiased selected-strategy OOS.
That claim is not supported by this project's actual research history:

- `app/data/backtest.json` already reports 1116 searches over exactly that year.
  It was committed in `fcb441f754daa9ff83843187d763c748f7fa9040` on
  2026-08-25T15:03:07+08:00, before P1 was frozen in
  `be0c9f409c42046239f4fa7d6589f47cd56e7e5e` on
  2026-08-26T12:58:22+08:00.
- `research/run_backtests.py`, line 210, chooses `robust_pick` by filtering for
  positive holdout returns and sorting on holdout return. This is direct use of
  that legacy holdout in candidate selection, not just overlapping dates.
- The existing factor report and real five-minute report use the same year.
  Their outcomes were also already inspected. File hashes and exact windows are
  recorded in `return-and-history-audit-A1.json`.

The new development loader's `holdoutLoaded: false` remains a valid statement
about that invocation. It does not erase earlier research exposure or certify
an untouched project-wide test set. This finding does not establish that all
144 new candidates are unprofitable or that their code leaks future rows; it
does invalidate the proposed *unbiased independent holdout* label for this year.

## Correction and remaining boundary

The current canonical contract now names this a reserved final evaluation
window with known prior exposure. It may provide descriptive historical
performance, not an untouched independent confirmation. Original P1 files and
configuration bytes remain immutable; this audit explicitly supersedes their
untouched/unopened wording. Both config and plan hashes are unchanged.

No replacement date range or new data-dependent acceptance criterion is chosen.
Independent validation requires a separately admitted protocol with defensible
research-history provenance and genuinely unseen evidence. A machine-enforced
prior-exposure gate has not yet been implemented and is required before any
future verified-strategy promotion. Current preflight output is input admission
only, not OOS certification. The current registry still has zero verified
strategies; it was not rewritten by this audit.

## Return check, not a new backtest

The legacy daily report contains +277.59% annualized for the full-window search
winner, and +144.23% for the holdout-selected candidate. Neither is newly
validated performance. The factor leaderboard's +46.42% annualized is also an
unadmitted legacy result. The selected real-five-minute run's 242 stored equity
snapshots were independently read: CNY 1,000,000 starting capital, CNY
630,438.928140677 ending equity, -36.9561071859% total return and
-46.4569308207% maximum drawdown. Recomputing those two metrics from the stored
equity confirms their arithmetic, not the realism or completeness of fills,
cash/share events or fees.

The new walk-forward database has 145 runs, all `kind=synthetic`, with 7356
events and every `verified_strategy=0`. Synthetic tests are not market returns.
A first read-only database check used the nonexistent name `qforge_study.sqlite`
and failed; listing actual local databases identified `qforge_walkforward.sqlite`.
The successful inventory query used that existing file in read-only mode; no
empty database was created and no failed probe was counted as evidence.

Verdict: high historical numbers exist, but zero >100%-annualized strategies
have passed the stated verification gates. There is no new market P&L result
from P1–P5. This audit narrows the claim rather than changing the goalposts.
