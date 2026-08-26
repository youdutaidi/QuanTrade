"""Zero-network synthetic ledger workflow, explicitly not a market backtest."""

from __future__ import annotations

import json
from pathlib import Path

from .ledger import PaperAccount
from .ledger_audit import audit_ledger
from .models import Distribution, OpeningQuote, OrderIntent
from .specification import StudySpec
from .store import load_ledger, persist_ledger


def run_ledger_demo(spec: StudySpec, root: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    account = _demo_account(spec.values["execution"])
    events = account.events
    audit = audit_ledger(events, spec.values["execution"])
    if not audit["allPass"]:
        raise ValueError(f"synthetic ledger failed independent replay: {audit}")
    receipt = persist_ledger(root / "research/data/qforge_walkforward.sqlite", spec, events, audit)
    restored, metadata = load_ledger(Path(receipt["database"]), receipt["runId"])
    replay = audit_ledger(restored, spec.values["execution"])
    if restored != events or not replay["allPass"] or not replay["allSessionsClosed"] or metadata["config_sha256"] != spec.sha256:
        raise ValueError("persisted ledger round-trip verification failed")
    result = {**receipt, "configSha256": spec.sha256, "accountingReplay": replay, "notMarketBacktest": True,
              "scope": "synthetic cash/share semantics only; no strategy return or source-action/tax verification"}
    for name, value in [("events.json", events), ("result.json", result)]:
        with (output / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return result


def _demo_account(policy: dict) -> PaperAccount:
    code, dates = "sh.600000", ["2026-07-01", "2026-07-02", "2026-07-03"]
    account = PaperAccount(policy, dates, "2026-06-30")
    account.begin_session(dates[0])
    account.execute(OrderIntent("demo-buy", code, "BUY", 1000, "2026-06-30", dates[0]),
                    OpeningQuote(code, dates[0], 10, 10, False, True, 10000, "2026-06-30"))
    account.close_session({code: 10}, {code: 10})
    account.begin_session(dates[1])
    account.book_distribution(Distribution("demo-distribution", code, dates[0], dates[1], 0.16, 0.1,
                                          dates[2], dates[2], 8.91, "synthetic-fixture",
                                          "explicit synthetic net cash; not an investor tax determination"))
    account.close_session({code: 8.91}, {code: 8.91})
    account.begin_session(dates[2])
    account.execute(OrderIntent("demo-sell", code, "SELL", 1100, dates[1], dates[2]),
                    OpeningQuote(code, dates[2], 9, 8.91, False, True, 10000, dates[1]))
    account.close_session({}, {code: 8.91})
    return account
