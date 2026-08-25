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

## Sources

- <https://github.com/zxygithub/baostock/blob/master/README.md>
- <https://github.com/zxygithub/baostock/blob/master/docs/data_download_plan.md>
