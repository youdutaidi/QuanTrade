# QF-DATA-EXPANSION-01 download protocol decision

## A1: concurrent sessions — protocol invalid

- Change: four BaoStock sessions fetched disjoint, atomically claimed security
  tasks while SQLite used WAL and short write transactions.
- Initial observation: 268 securities and 339,616 daily bars were written.
- Falsifier: one session changed from zero failures to 161 consecutive task
  failures after the concurrent sessions had been active.
- External constraint: the BaoStock project README warns that concurrent
  sessions can produce decompression and encoding errors.
- Verdict: protocol invalid. A zero-error prefix did not establish data
  integrity, so no rows from this attempt were retained.
- Recovery: `market reset-daily` deleted only daily bars and adjustment factors,
  preserved reference tables and universe audits, and reset 5,426 checkpoints.

## A2: single refreshed session — active

- Change: one network session at a time, refreshed every 200 securities, with a
  two-second pause between batches and 90-second request deadlines.
- Database writes remain idempotent and resumable per security.
- Admission requires all tasks complete, SQLite quick-check, semantic integrity
  queries, and a fresh-source deterministic sample replay.

## A3: full-call timeout and session circuit breaker — active

- A2 preserved 811 completed securities but exposed an unbounded wait before a
  BaoStock response object was returned.
- Recovery preserved all successful rows, released only running checkpoints,
  and resumed from the next security.
- Every API call and response stream now has a 90-second deadline. Any request
  exception marks only that task failed, closes the current session, pauses,
  and logs in again before the next task.
- Four benchmark indexes were added during the same recovery and downloaded
  successfully. The two symbols that triggered slow responses succeeded after
  a clean-session retry, supporting a transient-session explanation.

## A4: actual-attempt accounting and completion recovery — active

- A3 exposed an accounting bug: claiming a whole batch consumed an attempt for
  tasks that had not yet made a network request.
- Repair changed 3,919 unexecuted tasks from `running/3` to `pending/0` and 12
  actual failures from `failed/3` to `failed/1`. All 2,021,911 daily bars remained
  unchanged, verified by before/after row counts.
- Task claiming now reserves work without consuming a retry. Only the actual
  request path increments attempts. Regression tests cover this distinction.
- Login receives three bounded retries. The completion transaction catches
  transient download-pass errors and recovers running checkpoints on its next
  pass.
- All 12 previously failed symbols succeeded at the start of A4.

## Sources

- <https://github.com/zxygithub/baostock/blob/master/README.md>
- <https://github.com/zxygithub/baostock/blob/master/docs/data_download_plan.md>

## A5: partial-stream, coverage and price-basis audit

- A4 was stopped after 2,240 completed tasks and 2,975,440 daily bars. No market
  records were deleted. Its checkpoint recovery is delegated to the same single
  downloader after the A5 structural and semantic gates.
- A fake response reproduces an unsafe successful partial stream. Both a
  nonzero late error and an exhausted full page without confirmed EOF now fail
  closed. The adapter also rejects wrong codes, windows and adjustment flags.
- The first calendar comparison found 19 apparent one-day gaps among 1,917
  completed tasks. These were at the recorded delisting boundary, not inside
  their histories. A separate scan found only suspended rows at the delisting
  date. Such source rows remain raw evidence, not executable universe members.
- The SSE notice for 600190 identifies 2025-07-25 as its removal date; trading
  in its delisting period ended 2025-07-18. Source bars after its last trade are
  suspended. The calendar contract is IPO-inclusive and delisting-exclusive;
  missing interior days are rejected rather than filled.
- SQLite view migration v2 retains all raw tables. The pre-resume A5 audit
  checks 2,975,371 expected interior rows, finds zero missing dates, and retains
  69 optional suspended boundary rows. All nine integrity counts are zero.
- The adjusted-price chain is explicitly NOT an economic total-return ledger.
  Raw OHLC/preclose are retained. Extreme losses are no longer clipped;
  invalid or missing tradable returns stop export. Corporate-action P&L remains
  unverified until a separate cash/share accounting test passes.
- Gates: 49 tests passed; structure gate passed with zero findings. Full source
  completion, source replay and strategy verification remain pending.
- Boundary source: <https://www.sse.com.cn/disclosure/announcement/listing/stock/c/c_20250718_10785880.shtml>
