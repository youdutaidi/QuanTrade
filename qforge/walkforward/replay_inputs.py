"""Pure alignment of admitted daily inputs; this module never fetches prices."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .signals import candidate_scores, eligible_universe, market_residuals
from .specification import Candidate, StudySpec


FIELDS = ("close", "raw_open", "raw_close", "raw_preclose", "volume", "amount", "trade_status", "is_st")


@dataclass(frozen=True)
class ReplayInputs:
    """Aligned matrices are read-only by contract; no account state lives here."""
    sessions: tuple[str, ...]
    fields: dict[str, pd.DataFrame]
    listed: pd.DataFrame
    eligible: pd.DataFrame
    returns: pd.DataFrame
    market_returns: pd.Series
    capacity: pd.DataFrame
    capacity_asof: dict[str, str | None]


def prepare_replay_inputs(frame: pd.DataFrame, calendar: list[str], securities: pd.DataFrame, spec: StudySpec) -> ReplayInputs:
    spec.validate()
    dates = _calendar(calendar)
    stocks = _stock_lifecycles(securities, spec)
    rows = _daily_rows(frame, dates, stocks.index, spec.values["benchmark"])
    listed = lifecycle_mask(dates, stocks)
    symbols = listed.columns[listed.any()]
    if not len(symbols):
        raise ValueError("no ordinary stock lifecycle overlaps the calendar")
    listed = listed[symbols]
    stock_rows = rows[rows["symbol"].isin(symbols)]
    fields = {key: stock_rows.pivot(index="date", columns="symbol", values=key).reindex(index=dates, columns=symbols) for key in FIELDS}
    _check_coverage(fields, listed)
    benchmark = rows[rows["symbol"] == spec.values["benchmark"]].set_index("date")["close"].reindex(dates)
    if benchmark.isna().any() or not np.isfinite(benchmark).all() or benchmark.le(0).any():
        raise ValueError("benchmark is missing a positive adjusted-price close")
    eligible = eligible_universe(fields["amount"], fields["trade_status"], fields["is_st"], listed, spec)
    policy = spec.values["execution"]
    capacity = fields["volume"].shift(policy["volume_lag"]).rolling(policy["volume_lookback"]).median()
    capacity = np.floor(capacity * policy["share_volume_participation"]).fillna(0).astype("int64")
    sessions = tuple(day.date().isoformat() for day in dates)
    asof = {day: sessions[index - policy["volume_lag"]] if index >= policy["volume_lag"] else None for index, day in enumerate(sessions)}
    return ReplayInputs(sessions, fields, listed, eligible, fields["close"].pct_change(fill_method=None),
                        benchmark.pct_change(fill_method=None), capacity, asof)


def lifecycle_mask(dates: pd.DatetimeIndex, stocks: pd.DataFrame) -> pd.DataFrame:
    ipo = pd.to_datetime(stocks["ipo_date"], errors="raise")
    out = pd.to_datetime(stocks["out_date"].replace("", None), errors="raise")
    if ipo.isna().any() or (out.notna() & out.le(ipo)).any():
        raise ValueError("missing or invalid security lifecycle")
    days = dates.to_numpy()[:, None]
    mask = (days >= ipo.to_numpy()[None, :]) & (out.isna().to_numpy()[None, :] | (days < out.to_numpy()[None, :]))
    return pd.DataFrame(mask, index=dates, columns=stocks.index)


def build_score_cache(inputs: ReplayInputs, spec: StudySpec) -> dict[tuple, pd.DataFrame]:
    residuals = market_residuals(inputs.returns, inputs.market_returns, spec.values["signals"]["beta_lookback"])
    scores = {}
    for candidate in spec.candidates():
        key = signal_key(candidate)
        if key not in scores:
            scores[key] = candidate_scores(candidate, inputs.returns, residuals, inputs.eligible, spec)
    return scores


def signal_key(candidate: Candidate) -> tuple:
    return candidate.family, candidate.lookback, candidate.skip, candidate.window


def _calendar(calendar: list[str]) -> pd.DatetimeIndex:
    dates = pd.DatetimeIndex(pd.to_datetime(calendar, errors="raise"))
    if not len(dates) or dates.hasnans or dates.tz is not None or not dates.is_unique or not dates.is_monotonic_increasing:
        raise ValueError("calendar must contain ordered unique timezone-naive sessions")
    if not dates.equals(dates.normalize()):
        raise ValueError("daily calendar cannot contain intraday timestamps")
    return dates


def _stock_lifecycles(securities: pd.DataFrame, spec: StudySpec) -> pd.DataFrame:
    required = {"code", "ipo_date", "out_date", "security_type"}
    if not required <= set(securities.columns) or securities["code"].duplicated().any():
        raise ValueError("security lifecycle schema or identity invalid")
    rule = spec.values["universe"]
    mask = securities["security_type"].astype(str).eq(rule["security_type"])
    mask &= securities["code"].str.startswith(tuple(rule["prefixes"]))
    stocks = securities.loc[mask].set_index("code").sort_index()
    if stocks.empty:
        raise ValueError("no supported stock lifecycles")
    return stocks


def _daily_rows(frame: pd.DataFrame, dates: pd.DatetimeIndex, codes: pd.Index, benchmark: str) -> pd.DataFrame:
    if not {"date", "symbol", *FIELDS} <= set(frame.columns):
        raise ValueError("daily replay input schema is incomplete")
    rows = frame[["date", "symbol", *FIELDS]].copy()
    if rows["symbol"].isna().any():
        raise ValueError("daily bar is missing its security identity")
    rows["date"] = pd.to_datetime(rows["date"], errors="raise")
    if rows.duplicated(["date", "symbol"]).any() or not rows["date"].isin(dates).all():
        raise ValueError("duplicate bars or bars outside the explicit calendar")
    unknown = rows["symbol"].str.startswith(("sh.60", "sh.68", "sz.00", "sz.30")) & ~rows["symbol"].isin(codes)
    if unknown.any():
        raise ValueError("ordinary stock bar lacks its security lifecycle")
    rows = rows[rows["symbol"].isin([*codes, benchmark])].copy()
    for field in FIELDS:
        rows[field] = pd.to_numeric(rows[field], errors="raise")
        if np.isinf(rows[field].to_numpy(dtype=float)).any():
            raise ValueError("nonfinite daily replay input")
    return rows


def _check_coverage(fields: dict, listed: pd.DataFrame) -> None:
    if (~listed & fields["trade_status"].notna()).any().any():
        raise ValueError("stock bar appears outside its listed lifecycle")
    for key in ("trade_status", "is_st"):
        if (listed & ~fields[key].isin([0, 1])).any().any():
            raise ValueError("missing listed bar or unknown trading/ST status")
    tradable = listed & fields["trade_status"].eq(1)
    for key in ("volume", "amount"):
        if (listed & fields[key].lt(0)).any().any():
            raise ValueError("negative listed volume/amount")
        if (tradable & fields[key].isna()).any().any():
            raise ValueError("missing tradable volume/amount")
    for key in ("close", "raw_open", "raw_close", "raw_preclose"):
        if (tradable & (fields[key].isna() | fields[key].le(0))).any().any():
            raise ValueError("tradable session has a missing or invalid price")
