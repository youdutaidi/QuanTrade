# QF-DATA-EXPANSION-01-A7

Owner: `/root`; workdir: `/Users/cailingling/Desktop/quant-intelligence-lab`.
Baseline: `a7301e8`. Scope remains data completeness and reproducible research
inputs; no strategy outcomes or parameters were inspected or optimized.

## Discriminators and verdicts

- Source replay now checks both raw daily bars and adjustment-factor keys and
  values. A regression case with identical bars but changed factors is rejected.
  This remains same-source replay, not independent market truth or P&L proof.
- Chunked export at code `4d43701` transformed 3,709,150 real rows / 2,823 symbols
  in 11.33 seconds. Maximum resident memory was 533,086,208 bytes; no swaps.
  The candidate artifact is explicitly partial and not the configured final
  panel. SHA256: `d945ab19fcae58d2ef3f86ad40ab76269d7c5b3eea534c798e279e1d24c5d6cf`.
- The export preserves raw OHLC/preclose and records its adjusted-price basis
  and unverified corporate-action accounting in Parquet metadata. Chunked
  output matches the reference transform; a failed export leaves a previous
  artifact unchanged.
- Completion snapshots are append-only, with an atomic latest-result pointer.
  A missing calendar day, failed export, panel/calendar row-count disagreement,
  or mid-run source-code change prevents `ready`.
- `qforge market verify-panel --config configs/market_data.json` refuses an
  incomplete manifest, an incompatible configured data scope, an absent replay
  sample, a missing/replaced Parquet file, or inconsistent row counts.
- Final local gate: 62 tests passed, zero structure findings. Package 3,573
  lines; workflow scripts 89 lines; script/package ratio 0.0249. Prior daily,
  minute and validation tests retained; new tests are additive except a toy
  calendar fixture now explicitly includes its non-trading weekend dates.

## Execution and retained boundaries

The A5 source job continues under `77ce68f`; no second BaoStock session was
started. A7's fresh-source replay and final completion command must run after
that job exits. No market rows were deleted. Full data admission, corporate
action cash/share accounting, strategy search, independent ledger replay and
the 100% annualized strategy objective are not achieved by these data tests.

Resource check command:

```bash
/usr/bin/time -l .venv/bin/python research/data_workflows/export_research_panel.py \
  --config configs/market_data.json \
  --output research/data/qforge_daily_panel_candidate_A7.parquet
```

Evidence: `partial_export.log`, `tests_scope.log`, `structure_scope_report.json`,
and `live_data_audit.json`. API basis for incremental Parquet writing:
<https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetWriter.html>.
