from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from qforge.marketdata.admission import verify_completed_panel
from qforge.marketdata.complete import complete_market_data
from qforge.marketdata.config import MarketDataConfig
from qforge.marketdata.store import MarketDataStore


def daily_frame():
    return pd.DataFrame([{
        "code": "sh.600000", "trade_date": day, "open": 10, "high": 11, "low": 9, "close": 10.5,
        "preclose": 10, "volume": 100, "amount": 1000, "adjustflag": 3, "turnover": 1,
        "trade_status": 1, "pct_change": 5, "is_st": 0, "source": "BaoStock",
    } for day in ["2020-01-02", "2020-01-03"]])


class Provider:
    def __init__(self, **kwargs): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def daily_bars(self, *args): return daily_frame()
    def adjustment_factors(self, *args):
        return pd.DataFrame(columns=["code", "operation_date", "fore_adjust_factor", "back_adjust_factor", "adjust_factor", "source"])


def setup_reference(tmp_path, monkeypatch):
    import qforge.marketdata.service as service
    import qforge.marketdata.verify as verify

    monkeypatch.setattr(service, "BaoStockMarketProvider", Provider)
    monkeypatch.setattr(verify, "BaoStockMarketProvider", Provider)
    config = MarketDataConfig("test", "market.sqlite", "2020-01-02", "2020-01-03")
    store = MarketDataStore(tmp_path / config.database_path)
    store.initialize()
    store.upsert_securities(pd.DataFrame([{
        "code": "sh.600000", "code_name": "样本", "ipoDate": "1999-01-01", "outDate": "", "type": "1", "status": "1",
    }]))
    store.upsert_calendar(pd.DataFrame([{"calendar_date": day, "is_trading_day": 1} for day in [config.start, config.end]]))
    for day in [config.start, config.end]:
        store.upsert_observation(day, pd.DataFrame([{"code": "sh.600000", "code_name": "样本", "tradeStatus": "1"}]))
        store.audit_universe(day, ["1"], ["sh"])
    return config


def test_completion_flow_admits_exact_panel_and_rejects_tampering(tmp_path, monkeypatch):
    from dataclasses import replace

    config = setup_reference(tmp_path, monkeypatch)
    result = complete_market_data(config, tmp_path)
    assert result["state"] == "ready" and result["verification"]["sampleSize"] == 1
    manifest = Path(result["manifest"])
    assert verify_completed_panel(manifest, config)["rows"] == 2
    with pytest.raises(ValueError, match="requested data scope"):
        verify_completed_panel(manifest, replace(config, end="2020-01-06"))
    assert result["panel"]["corporateActionsVerified"] is False
    invalid = json.loads(manifest.read_text())
    invalid["state"] = "incomplete"
    other = tmp_path / "incomplete.json"
    other.write_text(json.dumps(invalid))
    with pytest.raises(ValueError, match="not ready"):
        verify_completed_panel(other)
    Path(result["panel"]["output"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="fingerprint changed"):
        verify_completed_panel(manifest)


def test_mid_run_code_change_cannot_claim_ready(tmp_path, monkeypatch):
    import qforge.marketdata.complete as module

    config = setup_reference(tmp_path, monkeypatch)
    monkeypatch.setattr(module, "market_code_sha256", lambda: "changed-after-start")
    result = complete_market_data(config, tmp_path)
    assert result["state"] == "incomplete"
    assert "code changed" in result["errors"][0]


def test_export_count_must_match_audited_calendar_coverage(tmp_path, monkeypatch):
    import qforge.marketdata.complete as module

    config = setup_reference(tmp_path, monkeypatch)
    original = module.export_research_panel

    def wrong_count(*args):
        return {**original(*args), "rows": 1}

    monkeypatch.setattr(module, "export_research_panel", wrong_count)
    result = complete_market_data(config, tmp_path)
    assert result["state"] == "incomplete"
    assert "audited calendar coverage" in result["errors"][0]
